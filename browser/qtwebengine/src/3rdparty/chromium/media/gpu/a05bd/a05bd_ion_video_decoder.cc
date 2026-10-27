// Copyright 2026 The TAB-A05-BD port contributors
// Use of this source code is governed by a BSD-style license that can be
// found in the Chromium LICENSE file.
#include "media/gpu/a05bd/a05bd_ion_video_decoder.h"

#include <cstdlib>
#include <cstring>
#include <sys/stat.h>
#include <unistd.h>
#include <gst/app/gstappsrc.h>
#include <gst/app/gstappsink.h>
#include <gst/video/video.h>
#include "base/functional/bind.h"
#include "base/logging.h"
#include "media/base/decoder_buffer.h"
#include "media/base/video_frame.h"
#include "third_party/libyuv/include/libyuv.h"

namespace media {
namespace {
constexpr char kPlugin[] = "/usr/local/lib/a05bd-gst-pts/libgsta05bdiondec.so";
constexpr size_t kQueueLimit = 4;
bool InitGstreamer() {
  static const bool ready = [] {
    if (!gst_init_check(nullptr, nullptr, nullptr)) return false;
    GError* error = nullptr;
    GstPlugin* plugin = gst_plugin_load_file(kPlugin, &error);
    if (error) {
      LOG(ERROR) << "A05bdIonDecoder plugin: " << error->message;
      g_error_free(error);
    }
    if (!plugin) return false;
    gst_object_unref(plugin);
    return true;
  }();
  return ready;
}
}  // namespace

// Each GStreamer callback owns a shared reference to this immutable bridge.
// Streaming threads only COPY the weak pointer and post it back to its owning
// sequence; they never dereference the decoder or touch its mutable state.
struct A05bdIonVideoDecoder::CallbackState {
  scoped_refptr<base::SequencedTaskRunner> runner;
  base::WeakPtr<A05bdIonVideoDecoder> decoder;
  void Wake() const {
    runner->PostTask(FROM_HERE,
                    base::BindOnce(&A05bdIonVideoDecoder::SchedulePump, decoder));
  }
};

bool A05bdIonVideoDecoder::IsSupported() {
  const char* enabled = std::getenv("A05BD_ION_HW_DECODE");
  struct stat st;
  return enabled && std::strcmp(enabled, "1") == 0 &&
         stat(kPlugin, &st) == 0 && S_ISREG(st.st_mode) && st.st_uid == 0 &&
         !(st.st_mode & (S_IWGRP | S_IWOTH)) &&
         access("/dev/video0", R_OK | W_OK) == 0 &&
         access("/dev/ion", R_OK | W_OK) == 0;
}

SupportedVideoDecoderConfigs A05bdIonVideoDecoder::GetSupportedConfigs() {
  // Device tests cover AVC up to 1080p. Do not advertise HEVC/VP9/4K or DRM.
  SupportedVideoDecoderConfigs configs;
  for (auto profile : {H264PROFILE_BASELINE, H264PROFILE_MAIN, H264PROFILE_HIGH})
    configs.emplace_back(profile, profile, gfx::Size(16,16),
                         gfx::Size(1920,1088), false, false);
  return configs;
}

A05bdIonVideoDecoder::A05bdIonVideoDecoder(
    scoped_refptr<base::SequencedTaskRunner> task_runner)
    : task_runner_(std::move(task_runner)) {
  DETACH_FROM_SEQUENCE(sequence_checker_);
}
A05bdIonVideoDecoder::~A05bdIonVideoDecoder() {
  DCHECK_CALLED_ON_VALID_SEQUENCE(sequence_checker_);
  weak_factory_.InvalidateWeakPtrs();
  StopPipeline();
  AbortPending();
}
VideoDecoderType A05bdIonVideoDecoder::GetDecoderType() const {
  return VideoDecoderType::kV4L2;
}
bool A05bdIonVideoDecoder::IsPlatformDecoder() const { return true; }
bool A05bdIonVideoDecoder::NeedsBitstreamConversion() const { return true; }
bool A05bdIonVideoDecoder::CanReadWithoutStalling() const { return true; }
int A05bdIonVideoDecoder::GetMaxDecodeRequests() const { return 4; }

void A05bdIonVideoDecoder::Initialize(
    const VideoDecoderConfig& config, bool, CdmContext*, InitCB init_cb,
    const OutputCB& output_cb, const WaitingCB&) {
  DCHECK_CALLED_ON_VALID_SEQUENCE(sequence_checker_);
  weak_factory_.InvalidateWeakPtrs();
  StopPipeline();
  auto weak = weak_factory_.GetWeakPtr();
  AbortPending();
  if (!weak) {
    std::move(init_cb).Run(DecoderStatus::Codes::kAborted);
    return;
  }
  if (!IsSupported() || !config.IsValidConfig() || config.is_encrypted() ||
      config.codec() != VideoCodec::kH264 ||
      (config.profile() != H264PROFILE_BASELINE && config.profile() != H264PROFILE_MAIN &&
       config.profile() != H264PROFILE_HIGH) ||
      config.coded_size().width() > 1920 || config.coded_size().height() > 1088 ||
      (config.coded_size().width() & 1) || (config.coded_size().height() & 1)) {
    std::move(init_cb).Run(DecoderStatus::Codes::kUnsupportedConfig);
    return;
  }
  config_ = config;
  output_cb_ = output_cb;
  failed_ = false;
  eos_sent_ = false;
  if (!InitGstreamer() || !StartPipeline()) {
    StopPipeline(); failed_ = true;
    std::move(init_cb).Run(DecoderStatus::Codes::kFailedToCreateDecoder);
    return;
  }
  LOG(INFO) << "A05bdIonDecoder: MT8168 ION/VCU -> owned I420; "
            << config.AsHumanReadableString();
  std::move(init_cb).Run(DecoderStatus::Codes::kOk);
}

bool A05bdIonVideoDecoder::StartPipeline() {
  GError* error = nullptr;
  pipeline_ = gst_parse_launch(
      "appsrc name=in format=time is-live=false block=false max-bytes=4194304 "
      "max-buffers=4 ! h264parse ! a05bdionh264dec ! "
      "appsink name=out sync=false max-buffers=4 drop=false", &error);
  if (error) {
    LOG(ERROR) << "A05bdIonDecoder pipeline: " << error->message;
    g_error_free(error);
    return false;
  }
  if (!pipeline_) return false;
  source_ = gst_bin_get_by_name(GST_BIN(pipeline_), "in");
  sink_ = gst_bin_get_by_name(GST_BIN(pipeline_), "out");
  bus_ = gst_element_get_bus(pipeline_);
  if (!source_ || !sink_ || !bus_) return false;
  GstCaps* caps = gst_caps_new_simple("video/x-h264", "stream-format", G_TYPE_STRING,
      "byte-stream", "alignment", G_TYPE_STRING, "au", nullptr);
  gst_app_src_set_caps(GST_APP_SRC(source_), caps); gst_caps_unref(caps);
  using Bridge = std::shared_ptr<CallbackState>;
  auto bridge = std::make_shared<CallbackState>();
  bridge->runner = task_runner_; bridge->decoder = weak_factory_.GetWeakPtr();
  auto destroy = [](gpointer p) { delete static_cast<Bridge*>(p); };
  GstAppSrcCallbacks src_callbacks = {};
  src_callbacks.need_data = [](GstAppSrc*, guint, gpointer p) {
    (*static_cast<Bridge*>(p))->Wake();
  };
  gst_app_src_set_callbacks(GST_APP_SRC(source_), &src_callbacks,
                           new Bridge(bridge), destroy);
  GstAppSinkCallbacks sink_callbacks = {};
  sink_callbacks.new_sample = [](GstAppSink*, gpointer p) -> GstFlowReturn {
    (*static_cast<Bridge*>(p))->Wake(); return GST_FLOW_OK;
  };
  sink_callbacks.eos = [](GstAppSink*, gpointer p) {
    (*static_cast<Bridge*>(p))->Wake();
  };
  gst_app_sink_set_callbacks(GST_APP_SINK(sink_), &sink_callbacks,
                            new Bridge(bridge), destroy);
  gst_bus_set_sync_handler(bus_, [](GstBus*, GstMessage* msg, gpointer p) {
    if (GST_MESSAGE_TYPE(msg) == GST_MESSAGE_ERROR || GST_MESSAGE_TYPE(msg) == GST_MESSAGE_EOS)
      (*static_cast<Bridge*>(p))->Wake();
    return GST_BUS_PASS;
  }, new Bridge(bridge), destroy);
  return gst_element_set_state(pipeline_, GST_STATE_PLAYING) != GST_STATE_CHANGE_FAILURE;
}

void A05bdIonVideoDecoder::StopPipeline() {
  if (pipeline_) gst_element_set_state(pipeline_, GST_STATE_NULL);
  if (bus_) gst_object_unref(bus_);
  if (sink_) gst_object_unref(sink_);
  if (source_) gst_object_unref(source_);
  if (pipeline_) gst_object_unref(pipeline_);
  pipeline_ = source_ = sink_ = nullptr; bus_ = nullptr;
  pump_posted_ = false;
}

void A05bdIonVideoDecoder::SchedulePump() {
  DCHECK_CALLED_ON_VALID_SEQUENCE(sequence_checker_);
  if (!pipeline_ || failed_ || pump_posted_) return;
  pump_posted_ = true;
  task_runner_->PostTask(FROM_HERE,
      base::BindOnce(&A05bdIonVideoDecoder::Pump, weak_factory_.GetWeakPtr()));
}

scoped_refptr<VideoFrame> A05bdIonVideoDecoder::CopySample(GstSample* sample) {
  GstVideoInfo info;
  gst_video_info_init(&info);
  if (!gst_video_info_from_caps(&info, gst_sample_get_caps(sample)) ||
      GST_VIDEO_INFO_FORMAT(&info) != GST_VIDEO_FORMAT_NV12) return nullptr;
  const int width = GST_VIDEO_INFO_WIDTH(&info), height = GST_VIDEO_INFO_HEIGHT(&info);
  if (width < 16 || height < 16 || width > 1920 || height > 1088 ||
      (width & 1) || (height & 1)) return nullptr;
  const gfx::Size size(width, height);
  if (!gfx::Rect(size).Contains(config_.visible_rect())) return nullptr;
  GstBuffer* buffer = gst_sample_get_buffer(sample);
  if (!GST_BUFFER_PTS_IS_VALID(buffer) || GST_BUFFER_PTS(buffer) / 1000 > INT64_MAX)
    return nullptr;
  auto frame = VideoFrame::CreateFrame(PIXEL_FORMAT_I420, size, config_.visible_rect(),
      config_.natural_size(), base::Microseconds(GST_BUFFER_PTS(buffer) / 1000));
  if (!frame) return nullptr;
  GstVideoFrame mapped;
  if (!gst_video_frame_map(&mapped, &info, buffer, GST_MAP_READ)) return nullptr;
  int result = libyuv::NV12ToI420(
      static_cast<const uint8_t*>(GST_VIDEO_FRAME_PLANE_DATA(&mapped,0)),
      GST_VIDEO_FRAME_PLANE_STRIDE(&mapped,0),
      static_cast<const uint8_t*>(GST_VIDEO_FRAME_PLANE_DATA(&mapped,1)),
      GST_VIDEO_FRAME_PLANE_STRIDE(&mapped,1),
      frame->writable_data(VideoFrame::kY), frame->stride(VideoFrame::kY),
      frame->writable_data(VideoFrame::kU), frame->stride(VideoFrame::kU),
      frame->writable_data(VideoFrame::kV), frame->stride(VideoFrame::kV), width, height);
  gst_video_frame_unmap(&mapped);
  if (result) return nullptr;
  frame->set_color_space(config_.color_space_info().ToGfxColorSpace());
  frame->metadata().power_efficient = true;
  return frame;
}

void A05bdIonVideoDecoder::Pump() {
  DCHECK_CALLED_ON_VALID_SEQUENCE(sequence_checker_);
  pump_posted_ = false;
  if (!pipeline_ || failed_) return;
  auto weak = weak_factory_.GetWeakPtr();
  GstMessage* error = gst_bus_pop_filtered(bus_, GST_MESSAGE_ERROR);
  if (error) {
    GError* detail = nullptr; gchar* debug = nullptr;
    gst_message_parse_error(error, &detail, &debug);
    LOG(ERROR) << "A05bdIonDecoder: " << (detail ? detail->message : "pipeline failure");
    if (detail) g_error_free(detail); g_free(debug); gst_message_unref(error);
    Fail(); return;
  }
  for (int i=0; i<8; ++i) {
    GstSample* sample = gst_app_sink_try_pull_sample(GST_APP_SINK(sink_), 0);
    if (!sample) break;
    auto frame = CopySample(sample); gst_sample_unref(sample);
    if (!frame) { Fail(); return; }
    output_cb_.Run(std::move(frame));
    if (!weak) return;
  }
  if (eos_sent_ && eos_cb_ && gst_app_sink_is_eos(GST_APP_SINK(sink_))) {
    auto cb = std::move(eos_cb_); std::move(cb).Run(DecoderStatus::Codes::kOk); return;
  }
  while (!pending_.empty() && !eos_sent_ &&
         gst_app_src_get_current_level_buffers(GST_APP_SRC(source_)) < kQueueLimit) {
    auto item = std::move(pending_.front()); pending_.pop_front();
    if (item.buffer->end_of_stream()) {
      eos_sent_ = true; eos_cb_ = std::move(item.callback);
      if (gst_app_src_end_of_stream(GST_APP_SRC(source_)) != GST_FLOW_OK) Fail();
      return;
    }
    if (item.buffer->timestamp().is_negative() || item.buffer->size() == 0 ||
        item.buffer->size() > 4*1024*1024 ||
        static_cast<uint64_t>(item.buffer->timestamp().InMicroseconds()) >= GST_CLOCK_TIME_NONE / GST_USECOND) {
      std::move(item.callback).Run(DecoderStatus::Codes::kFailed);
      if (weak) Fail(); return;
    }
    GstBuffer* buffer = gst_buffer_new_allocate(nullptr, item.buffer->size(), nullptr);
    if (!buffer) {
      std::move(item.callback).Run(DecoderStatus::Codes::kFailed);
      if (weak) Fail(); return;
    }
    if (gst_buffer_fill(buffer, 0, item.buffer->data(), item.buffer->size()) != item.buffer->size()) {
      gst_buffer_unref(buffer); std::move(item.callback).Run(DecoderStatus::Codes::kFailed);
      if (weak) Fail(); return;
    }
    GST_BUFFER_PTS(buffer) = item.buffer->timestamp().InMicroseconds() * GST_USECOND;
    if (item.buffer->duration().is_positive())
      GST_BUFFER_DURATION(buffer) = item.buffer->duration().InMicroseconds() * GST_USECOND;
    const GstFlowReturn result = gst_app_src_push_buffer(GST_APP_SRC(source_), buffer);
    std::move(item.callback).Run(result == GST_FLOW_OK ? DecoderStatus::Codes::kOk : DecoderStatus::Codes::kFailed);
    if (!weak) return;
    if (result != GST_FLOW_OK) { Fail(); return; }
  }
}

void A05bdIonVideoDecoder::Fail() {
  failed_ = true;
  weak_factory_.InvalidateWeakPtrs();
  StopPipeline();
  std::deque<PendingDecode> pending; pending.swap(pending_);
  auto eos = std::move(eos_cb_);
  if (eos) std::move(eos).Run(DecoderStatus::Codes::kFailed);
  for (auto& item : pending) std::move(item.callback).Run(DecoderStatus::Codes::kFailed);
}
void A05bdIonVideoDecoder::AbortPending() {
  std::deque<PendingDecode> pending; pending.swap(pending_); auto eos = std::move(eos_cb_);
  if (eos) std::move(eos).Run(DecoderStatus::Codes::kAborted);
  for (auto& item : pending) std::move(item.callback).Run(DecoderStatus::Codes::kAborted);
}
void A05bdIonVideoDecoder::Decode(scoped_refptr<DecoderBuffer> buffer, DecodeCB cb) {
  DCHECK_CALLED_ON_VALID_SEQUENCE(sequence_checker_);
  if (!pipeline_ || failed_ || eos_sent_ || pending_.size() >= kQueueLimit || (!buffer->end_of_stream() && buffer->is_encrypted())) {
    std::move(cb).Run(DecoderStatus::Codes::kFailed); return;
  }
  pending_.push_back({std::move(buffer), std::move(cb)}); SchedulePump();
}
void A05bdIonVideoDecoder::Reset(base::OnceClosure closure) {
  DCHECK_CALLED_ON_VALID_SEQUENCE(sequence_checker_);
  weak_factory_.InvalidateWeakPtrs(); StopPipeline();
  auto weak = weak_factory_.GetWeakPtr();
  AbortPending();
  if (!weak) { std::move(closure).Run(); return; }
  failed_ = false; eos_sent_ = false;
  if (!StartPipeline()) { StopPipeline(); failed_ = true; }
  std::move(closure).Run();
}
}  // namespace media
