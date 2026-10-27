/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Opt-in stateful H.264 decoder for the TAB-A05-BD vendor VCU ABI.
 * Uses ION multimedia DMA-BUFs for both queues. Native M21S is detiled,
 * never relabelled as linear NV12. No kernel or global GStreamer changes.
 */
#define _GNU_SOURCE
#include <gst/gst.h>
#include <gst/video/gstvideodecoder.h>
#include <gst/video/video-frame.h>
#include <linux/videodev2.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include <string.h>
#include "include/ion.h"
#include "include/ion_drv.h"

#define MAX_SRC 8
#define MAX_CAP 16
#define M21S v4l2_fourcc('M','2','1','S')
typedef struct { int handle,fd; guint8 *map; gsize size; gboolean queued,cached; } IonBuf;
typedef struct _GstA05bdIonDec {
    GstVideoDecoder parent;
    int video,ion;
    gboolean out_on,cap_on,ready,last;
    guint nsrc,ncap,width,height,stride,coded_height;
    guint input_size,decoded;
    IonBuf src[MAX_SRC],cap[MAX_CAP];
    GstVideoCodecState *input;
} GstA05bdIonDec;
typedef struct _GstA05bdIonDecClass { GstVideoDecoderClass parent_class; } GstA05bdIonDecClass;
G_DEFINE_TYPE(GstA05bdIonDec,gst_a05bd_ion_dec,GST_TYPE_VIDEO_DECODER)
GST_DEBUG_CATEGORY_STATIC(a05bd_debug);
#define GST_CAT_DEFAULT a05bd_debug

static int vio(GstA05bdIonDec *s,unsigned long req,void *arg,const char *name) {
    int r=ioctl(s->video,req,arg);
    if(r<0)GST_ERROR_OBJECT(s,"%s: %s",name,g_strerror(errno));
    return r;
}
static void init_buf(IonBuf *b) { memset(b,0,sizeof(*b));b->fd=-1;b->map=MAP_FAILED; }
static gboolean ion_alloc(GstA05bdIonDec *s,IonBuf *b,gsize size,guint port) {
    b->size=(size+4095)&~(gsize)4095;
    b->cached=port==(3<<5) && g_strcmp0(g_getenv("A05BD_ION_CAPTURE_CACHED"),"1")==0;
    struct ion_allocation_data a={.len=b->size,.align=4096,.heap_id_mask=1u<<10,
        .flags=b->cached?(ION_FLAG_CACHED|ION_FLAG_CACHED_NEEDS_SYNC):0};
    if(ioctl(s->ion,ION_IOC_ALLOC,&a)<0)goto fail;
    b->handle=a.handle;
    struct ion_mm_data mm={.mm_cmd=ION_MM_CONFIG_BUFFER};
    mm.config_buffer_param.handle=a.handle;mm.config_buffer_param.module_id=port;
    struct ion_custom_data custom={.cmd=ION_CMD_MULTIMEDIA,.arg=(uintptr_t)&mm};
    if(ioctl(s->ion,ION_IOC_CUSTOM,&custom)<0)goto fail;
    struct ion_fd_data fd={.handle=a.handle,.fd=-1};
    if(ioctl(s->ion,ION_IOC_SHARE,&fd)<0)goto fail;
    b->fd=fd.fd;b->map=mmap(NULL,b->size,PROT_READ|PROT_WRITE,MAP_SHARED,b->fd,0);
    if(b->map==MAP_FAILED)goto fail;
    return TRUE;
fail:
    GST_ERROR_OBJECT(s,"ION allocation/config/share/map failed: %s",g_strerror(errno));
    return FALSE;
}
static void ion_free(GstA05bdIonDec *s,IonBuf *b) {
    if(b->map!=MAP_FAILED)munmap(b->map,b->size);
    if(b->fd>=0)close(b->fd);
    if(b->handle && s->ion>=0){struct ion_handle_data h={.handle=b->handle};ioctl(s->ion,ION_IOC_FREE,&h);}
    init_buf(b);
}
static gboolean invalidate_capture(GstA05bdIonDec *s,IonBuf *b) {
    if(!b->cached)return TRUE;
    /* This vendor's DMA_BUF_IOCTL_SYNC only maps/unmaps kernel VA and does
     * not invalidate caches. Use its handle-based ION cache operation;
     * never perform a whole-system cache flush or pass arbitrary user VA. */
    struct ion_sys_data sys={.sys_cmd=ION_SYS_CACHE_SYNC};
    sys.cache_sync_param.handle=b->handle;
    sys.cache_sync_param.sync_type=ION_CACHE_INVALID_BY_RANGE;
    struct ion_custom_data custom={.cmd=ION_CMD_SYSTEM,.arg=(uintptr_t)&sys};
    if(ioctl(s->ion,ION_IOC_CUSTOM,&custom)<0) {
        GST_ERROR_OBJECT(s,"capture cache invalidation: %s",g_strerror(errno));return FALSE;
    }
    return TRUE;
}
static void backend_close(GstA05bdIonDec *s) {
    if(s->video>=0) {
        if(s->out_on){enum v4l2_buf_type t=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE;vio(s,VIDIOC_STREAMOFF,&t,"output streamoff");}
        if(s->cap_on){enum v4l2_buf_type t=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;vio(s,VIDIOC_STREAMOFF,&t,"capture streamoff");}
        close(s->video);s->video=-1;
    }
    for(guint i=0;i<MAX_SRC;i++)ion_free(s,&s->src[i]);
    for(guint i=0;i<MAX_CAP;i++)ion_free(s,&s->cap[i]);
    if(s->ion>=0){close(s->ion);s->ion=-1;}
    s->out_on=s->cap_on=s->ready=s->last=FALSE;s->nsrc=s->ncap=0;
}
static gboolean backend_open(GstA05bdIonDec *s) {
    s->ion=open("/dev/ion",O_RDWR|O_CLOEXEC);
    s->video=open("/dev/video0",O_RDWR|O_NONBLOCK|O_CLOEXEC);
    if(s->ion<0 || s->video<0) {
        GST_ERROR_OBJECT(s,"open ion/video0: %s",g_strerror(errno));return FALSE;
    }
    struct v4l2_capability cap={0};
    if(vio(s,VIDIOC_QUERYCAP,&cap,"querycap")<0 || strcmp((char *)cap.driver,"mtk-vcodec-dec")) {
        GST_ERROR_OBJECT(s,"refusing device with a different driver");return FALSE;
    }
    guint w=GST_VIDEO_INFO_WIDTH(&s->input->info),h=GST_VIDEO_INFO_HEIGHT(&s->input->info);
    if(!w || !h || w>1920 || h>1088 || (w&1) || (h&1)) {
        GST_ERROR_OBJECT(s,"unsupported coded size %ux%u",w,h);return FALSE;
    }
    s->input_size=MAX(1024u*1024u,((w*h*2u)+4095u)&~4095u);
    struct v4l2_format f={.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE};
    f.fmt.pix_mp.width=w;f.fmt.pix_mp.height=h;
    f.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_H264;f.fmt.pix_mp.num_planes=1;
    f.fmt.pix_mp.plane_fmt[0].sizeimage=s->input_size;
    if(vio(s,VIDIOC_S_FMT,&f,"H264 output format")<0)return FALSE;
    s->input_size=MAX(s->input_size,f.fmt.pix_mp.plane_fmt[0].sizeimage);
    struct v4l2_event_subscription sub={.type=V4L2_EVENT_SOURCE_CHANGE};
    if(vio(s,VIDIOC_SUBSCRIBE_EVENT,&sub,"source change subscribe")<0)return FALSE;
    struct v4l2_requestbuffers req={.count=MAX_SRC,.type=f.type,.memory=V4L2_MEMORY_DMABUF};
    if(vio(s,VIDIOC_REQBUFS,&req,"output DMABUF buffers")<0 || !req.count || req.count>MAX_SRC)return FALSE;
    s->nsrc=req.count;
    for(guint i=0;i<s->nsrc;i++)if(!ion_alloc(s,&s->src[i],s->input_size,(3<<5)|7))return FALSE;
    return TRUE;
}
static gboolean capture_queue(GstA05bdIonDec *s,guint index) {
    struct v4l2_plane p={.m.fd=s->cap[index].fd,.length=s->cap[index].size};
    struct v4l2_buffer b={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE,.memory=V4L2_MEMORY_DMABUF,.index=index,.length=1,.m.planes=&p};
    return vio(s,VIDIOC_QBUF,&b,"capture queue")==0;
}
static gboolean setup_capture(GstA05bdIonDec *s) {
    struct v4l2_format f={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE};
    if(vio(s,VIDIOC_G_FMT,&f,"header capture format")<0)return FALSE;
    if(f.fmt.pix_mp.pixelformat!=M21S || f.fmt.pix_mp.num_planes!=1) {
        GST_ERROR_OBJECT(s,"unsupported native output format (only verified 8-bit M21S)");return FALSE;
    }
    if(vio(s,VIDIOC_S_FMT,&f,"native capture format")<0 || vio(s,VIDIOC_G_FMT,&f,"capture actual sizes")<0)return FALSE;
    s->stride=f.fmt.pix_mp.plane_fmt[0].bytesperline;
    s->coded_height=f.fmt.pix_mp.height;
    struct v4l2_selection sel={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE,.target=V4L2_SEL_TGT_COMPOSE};
    s->width=GST_VIDEO_INFO_WIDTH(&s->input->info);s->height=GST_VIDEO_INFO_HEIGHT(&s->input->info);
    if(ioctl(s->video,VIDIOC_G_SELECTION,&sel)==0 && sel.r.width && sel.r.height) {
        if(sel.r.left || sel.r.top){GST_ERROR_OBJECT(s,"nonzero crop origin unsupported");return FALSE;}
        s->width=sel.r.width;s->height=sel.r.height;
    }
    if(!s->stride || (s->stride%16) || (s->coded_height%32) || s->width>s->stride || s->height>s->coded_height || (s->width&1) || (s->height&1))return FALSE;
    guint required=s->stride*s->coded_height*3u/2u;
    if(f.fmt.pix_mp.plane_fmt[0].sizeimage<required){GST_ERROR_OBJECT(s,"native buffer too small");return FALSE;}
    struct v4l2_control ctl={.id=V4L2_CID_MIN_BUFFERS_FOR_CAPTURE};
    if(vio(s,VIDIOC_G_CTRL,&ctl,"capture DPB minimum")<0 || ctl.value<1 || ctl.value>MAX_CAP-2)return FALSE;
    struct v4l2_requestbuffers req={.count=ctl.value+2,.type=f.type,.memory=V4L2_MEMORY_DMABUF};
    if(vio(s,VIDIOC_REQBUFS,&req,"capture DMABUF buffers")<0 || !req.count || req.count>MAX_CAP)return FALSE;
    s->ncap=req.count;
    for(guint i=0;i<s->ncap;i++) {
        if(!ion_alloc(s,&s->cap[i],f.fmt.pix_mp.plane_fmt[0].sizeimage,(3<<5)))return FALSE;
        if(!capture_queue(s,i))return FALSE;
    }
    GstVideoCodecState *out=gst_video_decoder_set_output_state(GST_VIDEO_DECODER(s),GST_VIDEO_FORMAT_NV12,s->width,s->height,s->input);
    gst_video_codec_state_unref(out);
    if(!gst_video_decoder_negotiate(GST_VIDEO_DECODER(s)))return FALSE;
    enum v4l2_buf_type type=f.type;
    if(vio(s,VIDIOC_STREAMON,&type,"capture streamon")<0)return FALSE;
    s->cap_on=s->ready=TRUE;
    GST_INFO_OBJECT(s,"ION hardware decoder ready: visible %ux%u, stride=%u coded_height=%u DPB=%d",s->width,s->height,s->stride,s->coded_height,ctl.value);
    return TRUE;
}
static void reclaim_sources(GstA05bdIonDec *s) {
    for(;;) {
        struct v4l2_plane p={0};struct v4l2_buffer b={.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,.memory=V4L2_MEMORY_DMABUF,.length=1,.m.planes=&p};
        if(ioctl(s->video,VIDIOC_DQBUF,&b)<0)break;
        if(b.index<s->nsrc)s->src[b.index].queued=FALSE;
    }
}
static void detile_plane(const guint8 *src,guint stride,guint tile_h,guint8 *dst,gint dst_stride,guint w,guint h) {
    for(guint y=0;y<h;y++)for(guint x=0;x<w;x+=16) {
        gsize offset=((gsize)(y/tile_h)*(stride/16)+x/16)*tile_h*16+(y%tile_h)*16;
        memcpy(dst+(gsize)y*dst_stride+x,src+offset,MIN(16,w-x));
    }
}
static GstFlowReturn receive_frames(GstA05bdIonDec *s) {
    if(!s->ready)return GST_FLOW_OK;
    for(;;) {
        struct v4l2_plane p={0};struct v4l2_buffer b={.type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE,.memory=V4L2_MEMORY_DMABUF,.length=1,.m.planes=&p};
        if(ioctl(s->video,VIDIOC_DQBUF,&b)<0) {
            if(errno==EAGAIN || errno==EPIPE)return GST_FLOW_OK;
            GST_ERROR_OBJECT(s,"capture dequeue: %s",g_strerror(errno));return GST_FLOW_ERROR;
        }
        if(b.index>=s->ncap || p.bytesused>s->cap[b.index].size)return GST_FLOW_ERROR;
        if(p.bytesused && !(b.flags&V4L2_BUF_FLAG_ERROR)) {
            if(p.bytesused<(gsize)s->stride*s->coded_height*3u/2u || !invalidate_capture(s,&s->cap[b.index]))return GST_FLOW_ERROR;
            /* This vendor marks LAST on input_max_ts during STOP. Decode-order
             * IDs are not presentation timestamps for B-frames: they can mark
             * LAST before a delayed reference picture. Preserve real PTS so
             * the highest timestamp is also the final displayed picture. */
            guint64 stamp=(guint64)b.timestamp.tv_sec*G_USEC_PER_SEC+b.timestamp.tv_usec;
            GList *queued=gst_video_decoder_get_frames(GST_VIDEO_DECODER(s));
            GstVideoCodecFrame *frame=NULL;
            guint matches=0;
            for(GList *it=queued;it;it=it->next) {
                GstVideoCodecFrame *candidate=it->data;
                if(GST_CLOCK_TIME_IS_VALID(candidate->pts) && candidate->pts/GST_USECOND==stamp) {
                    matches++;
                    if(!frame)frame=gst_video_codec_frame_ref(candidate);
                }
            }
            g_list_free_full(queued,(GDestroyNotify)gst_video_codec_frame_unref);
            if(matches!=1) {
                if(frame)gst_video_codec_frame_unref(frame);
                GST_ERROR_OBJECT(s,"missing or ambiguous output PTS %" G_GUINT64_FORMAT,stamp);
                return GST_FLOW_ERROR;
            }
            guint32 number=frame->system_frame_number;
            GstFlowReturn ret=gst_video_decoder_allocate_output_frame(GST_VIDEO_DECODER(s),frame);
            if(ret!=GST_FLOW_OK){gst_video_codec_frame_unref(frame);return ret;}
            GstVideoCodecState *out=gst_video_decoder_get_output_state(GST_VIDEO_DECODER(s));
            GstVideoFrame mapped;
            if(!gst_video_frame_map(&mapped,&out->info,frame->output_buffer,GST_MAP_WRITE)) {
                gst_video_codec_state_unref(out);gst_video_codec_frame_unref(frame);return GST_FLOW_ERROR;
            }
            const guint8 *native=s->cap[b.index].map;
            detile_plane(native,s->stride,32,GST_VIDEO_FRAME_PLANE_DATA(&mapped,0),GST_VIDEO_FRAME_PLANE_STRIDE(&mapped,0),s->width,s->height);
            detile_plane(native+(gsize)s->stride*s->coded_height,s->stride,16,GST_VIDEO_FRAME_PLANE_DATA(&mapped,1),GST_VIDEO_FRAME_PLANE_STRIDE(&mapped,1),s->width,s->height/2);
            gst_video_frame_unmap(&mapped);gst_video_codec_state_unref(out);
            ret=gst_video_decoder_finish_frame(GST_VIDEO_DECODER(s),frame);s->decoded++;
            GST_LOG_OBJECT(s,"hardware frame %u complete (%u total)",number,s->decoded);
            if(ret!=GST_FLOW_OK)return ret;
        } else if(b.flags&V4L2_BUF_FLAG_ERROR) {
            GST_ERROR_OBJECT(s,"hardware reported corrupt output");return GST_FLOW_ERROR;
        }
        if(b.flags&V4L2_BUF_FLAG_LAST){s->last=TRUE;return GST_FLOW_OK;}
        if(!capture_queue(s,b.index))return GST_FLOW_ERROR;
    }
}
static gboolean start(GstVideoDecoder *dec) {
    GstA05bdIonDec *s=(GstA05bdIonDec *)dec;s->decoded=0;
    gst_video_decoder_set_packetized(dec,TRUE);gst_video_decoder_set_needs_format(dec,TRUE);return TRUE;
}
static gboolean set_format(GstVideoDecoder *dec,GstVideoCodecState *state) {
    GstA05bdIonDec *s=(GstA05bdIonDec *)dec;backend_close(s);
    if(s->input)gst_video_codec_state_unref(s->input);
    s->input=gst_video_codec_state_ref(state);
    return backend_open(s);
}
static GstFlowReturn handle_frame(GstVideoDecoder *dec,GstVideoCodecFrame *frame) {
    GstA05bdIonDec *s=(GstA05bdIonDec *)dec;GstFlowReturn ret=GST_FLOW_ERROR;
    gint slot=-1;
    for(guint tries=0;tries<200;tries++) {
        reclaim_sources(s);
        for(guint i=0;i<s->nsrc;i++)if(!s->src[i].queued){slot=i;break;}
        if(slot>=0)break;
        ret=receive_frames(s);if(ret!=GST_FLOW_OK)goto done;
        struct pollfd pfd={.fd=s->video,.events=POLLIN|POLLOUT};poll(&pfd,1,5);
    }
    if(slot<0){GST_ERROR_OBJECT(s,"no source buffer returned");ret=GST_FLOW_ERROR;goto done;}
    gsize n=gst_buffer_get_size(frame->input_buffer);
    if(!n || n>s->src[slot].size){GST_ERROR_OBJECT(s,"access unit too large: %zu",n);ret=GST_FLOW_ERROR;goto done;}
    if(gst_buffer_extract(frame->input_buffer,0,s->src[slot].map,n)!=n){ret=GST_FLOW_ERROR;goto done;}
    struct v4l2_plane p={.m.fd=s->src[slot].fd,.length=s->src[slot].size,.bytesused=n};
    struct v4l2_buffer b={.type=V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE,.memory=V4L2_MEMORY_DMABUF,.index=slot,.length=1,.m.planes=&p,.flags=V4L2_BUF_FLAG_TIMESTAMP_COPY};
    if(!GST_CLOCK_TIME_IS_VALID(frame->pts)) {
        GST_ERROR_OBJECT(s,"hardware decoder requires presentation timestamps");
        ret=GST_FLOW_ERROR;goto done;
    }
    b.timestamp.tv_sec=frame->pts/GST_SECOND;
    b.timestamp.tv_usec=(frame->pts/GST_USECOND)%G_USEC_PER_SEC;
    if(vio(s,VIDIOC_QBUF,&b,"input access unit")<0){ret=GST_FLOW_ERROR;goto done;}
    s->src[slot].queued=TRUE;
    if(!s->out_on) {
        enum v4l2_buf_type type=b.type;
        if(vio(s,VIDIOC_STREAMON,&type,"output streamon")<0){ret=GST_FLOW_ERROR;goto done;}
        s->out_on=TRUE;
        struct v4l2_event ev={0};gboolean header=FALSE;
        for(guint i=0;i<100;i++) {
            if(ioctl(s->video,VIDIOC_DQEVENT,&ev)==0 && ev.type==V4L2_EVENT_SOURCE_CHANGE){header=TRUE;break;}
            struct pollfd pfd={.fd=s->video,.events=POLLPRI};poll(&pfd,1,5);
        }
        if(!header || !setup_capture(s)){GST_ERROR_OBJECT(s,"initial header/capture setup failed");ret=GST_FLOW_ERROR;goto done;}
    }
    {struct pollfd pfd={.fd=s->video,.events=POLLIN};poll(&pfd,1,10);}
    ret=receive_frames(s);
done:
    gst_video_codec_frame_unref(frame);
    return ret;
}
static GstFlowReturn finish(GstVideoDecoder *dec) {
    GstA05bdIonDec *s=(GstA05bdIonDec *)dec;
    if(!s->ready)return GST_FLOW_OK;
    struct v4l2_decoder_cmd cmd={.cmd=V4L2_DEC_CMD_STOP};
    if(vio(s,VIDIOC_DECODER_CMD,&cmd,"drain")<0)return GST_FLOW_ERROR;
    for(guint i=0;i<300 && !s->last;i++) {
        GstFlowReturn ret=receive_frames(s);if(ret!=GST_FLOW_OK)return ret;
        reclaim_sources(s);
        if(!s->last){struct pollfd pfd={.fd=s->video,.events=POLLIN};poll(&pfd,1,10);}
    }
    GST_INFO_OBJECT(s,"drain complete: decoded=%u last=%d",s->decoded,s->last);
    return s->last?GST_FLOW_OK:GST_FLOW_ERROR;
}
static gboolean stop(GstVideoDecoder *dec) {
    GstA05bdIonDec *s=(GstA05bdIonDec *)dec;backend_close(s);
    if(s->input){gst_video_codec_state_unref(s->input);s->input=NULL;}return TRUE;
}
static gboolean flush(GstVideoDecoder *dec) {
    GstA05bdIonDec *s=(GstA05bdIonDec *)dec;backend_close(s);
    return !s->input || backend_open(s);
}
static void gst_a05bd_ion_dec_init(GstA05bdIonDec *s) {
    s->video=s->ion=-1;
    for(guint i=0;i<MAX_SRC;i++)init_buf(&s->src[i]);
    for(guint i=0;i<MAX_CAP;i++)init_buf(&s->cap[i]);
}
static void gst_a05bd_ion_dec_class_init(GstA05bdIonDecClass *klass) {
    GstElementClass *element=GST_ELEMENT_CLASS(klass);
    GstVideoDecoderClass *decoder=GST_VIDEO_DECODER_CLASS(klass);
    gst_element_class_set_static_metadata(element,"MT8168 ION H264 decoder (experimental)","Codec/Decoder/Video/Hardware","Opt-in vendor VCU decode with verified M21S detiling","TAB-A05-BD port");
    static GstStaticPadTemplate sink=GST_STATIC_PAD_TEMPLATE("sink",GST_PAD_SINK,GST_PAD_ALWAYS,GST_STATIC_CAPS("video/x-h264,stream-format=(string)byte-stream,alignment=(string)au"));
    static GstStaticPadTemplate src=GST_STATIC_PAD_TEMPLATE("src",GST_PAD_SRC,GST_PAD_ALWAYS,GST_STATIC_CAPS("video/x-raw,format=(string)NV12,width=(int)[2,1920],height=(int)[2,1088]"));
    gst_element_class_add_static_pad_template(element,&sink);gst_element_class_add_static_pad_template(element,&src);
    decoder->start=start;decoder->set_format=set_format;decoder->handle_frame=handle_frame;
    decoder->finish=finish;decoder->drain=finish;decoder->stop=stop;decoder->flush=flush;
}
static gboolean plugin_init(GstPlugin *plugin) {
    GST_DEBUG_CATEGORY_INIT(a05bd_debug,"a05bdiondec",0,"TAB-A05-BD ION decoder");
    return gst_element_register(plugin,"a05bdionh264dec",GST_RANK_NONE,gst_a05bd_ion_dec_get_type());
}
#ifndef PACKAGE
#define PACKAGE "a05bd-ion-decoder"
#endif
GST_PLUGIN_DEFINE(GST_VERSION_MAJOR,GST_VERSION_MINOR,a05bdiondec,"MT8168 ION hardware decoder",plugin_init,"0.3.0","LGPL","a05bd-ion-decoder","https://docs.ubports.com/")
