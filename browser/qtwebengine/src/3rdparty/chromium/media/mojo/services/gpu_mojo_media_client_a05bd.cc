// Copyright 2026 The TAB-A05-BD port contributors
// Use of this source code is governed by a BSD-style license that can be
// found in the Chromium LICENSE file.
#include "media/mojo/services/gpu_mojo_media_client.h"
#include "media/gpu/a05bd/a05bd_ion_video_decoder.h"

namespace media {
class GpuMojoMediaClientA05bd final : public GpuMojoMediaClient {
 public:
  explicit GpuMojoMediaClientA05bd(GpuMojoMediaClientTraits& traits)
      : GpuMojoMediaClient(traits) {}
  ~GpuMojoMediaClientA05bd() override = default;
 protected:
  std::unique_ptr<VideoDecoder> CreatePlatformVideoDecoder(VideoDecoderTraits& traits) override {
    if (!A05bdIonVideoDecoder::IsSupported() || traits.oop_video_decoder) return nullptr;
    return std::make_unique<A05bdIonVideoDecoder>(traits.task_runner);
  }
#if BUILDFLAG(USE_LINUX_VIDEO_ACCELERATION)
  void NotifyPlatformDecoderSupport(
      mojo::PendingRemote<mojom::VideoDecoder> decoder,
      base::OnceCallback<void(mojo::PendingRemote<mojom::VideoDecoder>)> cb) override {
    std::move(cb).Run(std::move(decoder));
  }
#endif
  std::optional<SupportedVideoDecoderConfigs> GetPlatformSupportedVideoDecoderConfigs() override {
    if (!A05bdIonVideoDecoder::IsSupported()) return std::nullopt;
    return A05bdIonVideoDecoder::GetSupportedConfigs();
  }
  VideoDecoderType GetPlatformDecoderImplementationType() override {
    return A05bdIonVideoDecoder::IsSupported() ? VideoDecoderType::kV4L2 : VideoDecoderType::kUnknown;
  }
};
std::unique_ptr<GpuMojoMediaClient> CreateGpuMediaService(GpuMojoMediaClientTraits& traits) {
  return std::make_unique<GpuMojoMediaClientA05bd>(traits);
}
}  // namespace media
