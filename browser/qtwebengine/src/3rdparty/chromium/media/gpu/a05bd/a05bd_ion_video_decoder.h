// Copyright 2026 The TAB-A05-BD port contributors
// Use of this source code is governed by a BSD-style license that can be
// found in the Chromium LICENSE file.
#ifndef MEDIA_GPU_A05BD_ION_VIDEO_DECODER_H_
#define MEDIA_GPU_A05BD_ION_VIDEO_DECODER_H_

#include <deque>
#include <memory>
#include "base/memory/weak_ptr.h"
#include "base/task/sequenced_task_runner.h"
#include "media/base/video_decoder.h"
#include "media/base/video_decoder_config.h"
#include "media/base/supported_video_decoder_config.h"
#include "media/gpu/media_gpu_export.h"

typedef struct _GstElement GstElement;
typedef struct _GstBus GstBus;
typedef struct _GstSample GstSample;

namespace media {
// Experimental MT8168 stateful VCU backend. Only the explicit, unranked ION
// decoder is used. Decoded NV12 is copied into owned Chromium I420 frames.
class MEDIA_GPU_EXPORT A05bdIonVideoDecoder final : public VideoDecoder {
 public:
  static bool IsSupported();
  static SupportedVideoDecoderConfigs GetSupportedConfigs();
  explicit A05bdIonVideoDecoder(
      scoped_refptr<base::SequencedTaskRunner> task_runner);
  ~A05bdIonVideoDecoder() override;
  VideoDecoderType GetDecoderType() const override;
  bool IsPlatformDecoder() const override;
  bool NeedsBitstreamConversion() const override;
  bool CanReadWithoutStalling() const override;
  int GetMaxDecodeRequests() const override;
  void Initialize(const VideoDecoderConfig&, bool, CdmContext*, InitCB,
                  const OutputCB&, const WaitingCB&) override;
  void Decode(scoped_refptr<DecoderBuffer>, DecodeCB) override;
  void Reset(base::OnceClosure) override;

 private:
  struct PendingDecode {
    scoped_refptr<DecoderBuffer> buffer;
    DecodeCB callback;
  };
  struct CallbackState;
  bool StartPipeline();
  void StopPipeline();
  void SchedulePump();
  void Pump();
  void Fail();
  void AbortPending();
  scoped_refptr<VideoFrame> CopySample(GstSample*);

  scoped_refptr<base::SequencedTaskRunner> task_runner_;
  VideoDecoderConfig config_;
  OutputCB output_cb_;
  std::deque<PendingDecode> pending_;
  DecodeCB eos_cb_;
  GstElement* pipeline_ = nullptr;
  GstElement* source_ = nullptr;
  GstElement* sink_ = nullptr;
  GstBus* bus_ = nullptr;
  bool failed_ = false;
  bool eos_sent_ = false;
  bool pump_posted_ = false;
  SEQUENCE_CHECKER(sequence_checker_);
  base::WeakPtrFactory<A05bdIonVideoDecoder> weak_factory_{this};
};
}  // namespace media
#endif
