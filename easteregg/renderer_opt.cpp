#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <string>

#include "easteregg/easteregg.h"
#include "include/core/SkBitmap.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkData.h"
#include "include/core/SkFontMgr.h"
#include "include/core/SkImage.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkSerialProcs.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/core/SkTypeface.h"
#include "include/encode/SkPngEncoder.h"
#include "include/gpu/ganesh/GrDirectContext.h"
#include "include/gpu/ganesh/SkSurfaceGanesh.h"
#include "include/gpu/graphite/Context.h"
#include "include/gpu/graphite/Recording.h"
#include "include/gpu/graphite/Surface.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordOpts.h"
#include "tools/flags/CommandLineFlags.h"
#include "tools/fonts/FontToolUtils.h"
#include "tools/ganesh/GrContextFactory.h"
#include "tools/graphite/ContextFactory.h"
#include "tools/graphite/GraphiteToolUtils.h"
#include "tools/graphite/TestOptions.h"
#include "tools/gpu/ContextType.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "output.png", "Output .png file path");
static DEFINE_bool(opt, false, "Apply optimizer transforms before rendering");
static DEFINE_string(
        backend,
        "raster",
        "Render backend: raster (default), gl, grmtl, or grvk");
static DEFINE_int(cullmax, 0, "Maximum width or height to render; 0 disables extra culling");
static DEFINE_string(transform, "easteregg",
                     "Transform to run when --opt=true: easteregg, skrecordopt, or none");

static sk_sp<SkImage> DeserializeImageLikeDM(const void* data, size_t size, void*) {
    sk_sp<SkData> tmpData = SkData::MakeWithoutCopy(data, size);
    sk_sp<SkImage> image = SkImages::DeferredFromEncodedData(std::move(tmpData));
    return image ? image->makeRasterImage(nullptr) : nullptr;
}

static sk_sp<SkTypeface> DeserializeTypefaceLikeDM(const void* data, size_t, void*) {
    SkStream** stream = reinterpret_cast<SkStream**>(const_cast<void*>(data));
    return SkTypeface::MakeDeserialize(*stream, ToolUtils::TestFontMgr());
}

static sk_sp<SkPicture> LoadPictureLikeDM(const std::string& path) {
    std::unique_ptr<SkStream> stream = SkStream::MakeFromFile(path.c_str());
    if (!stream) {
        return nullptr;
    }

    SkDeserialProcs procs;
    procs.fImageProc = DeserializeImageLikeDM;
    procs.fTypefaceProc = DeserializeTypefaceLikeDM;
    return SkPicture::MakeFromStream(stream.get(), &procs);
}

static sk_sp<SkPicture> PictureFromRecord(const SkRecord& records, const SkRect& bounds) {
    SkPictureRecorder recorder;
    SkCanvas* canvas = recorder.beginRecording(bounds);
    if (!canvas) {
        return nullptr;
    }
    SkRecordDraw(records, canvas, nullptr, nullptr, 0, nullptr, nullptr);
    return recorder.finishRecordingAsPicture();
}

static sk_sp<SkPicture> MaybeOptimize(sk_sp<SkPicture> picture, const std::string& transform,
                                      bool doOpt) {
    if (!doOpt || !picture) {
        return picture;
    }

    SkRect bounds = picture->cullRect();
    SkRecord records;
    SkRecordCanvas recorder(&records, bounds);
    picture->playback(&recorder);

    RemoveOpaqueSaveLayerPass opt1;
    // CopyRemoveOpaqueSaveLayer opt1;
    RemoveLoneLuma opt2;
    GradientDstInToMasks opt3;
    DstInToClip opt4;

    if (transform == "none") {
        // no-op
    } else if (transform == "skrecordopt") {
        SkRecordOptimize(&records);
    } else if (transform == "easteregg") {
        opt3.transform(&records);
        opt2.transform(&records);
        opt4.transform(&records);
        opt1.transform(&records);
    } else {
        ERROR("Unknown transform '%s' (expected easteregg, skrecordopt, or none)",
              transform.c_str());
        return nullptr;
    }

    return PictureFromRecord(records, bounds);
}

static SkISize DMViewportSize(const sk_sp<SkPicture>& picture) {
    return picture->cullRect().roundOut().size();
}

static SkImageInfo MakeImageInfo(const SkISize& size) {
    return SkImageInfo::MakeN32Premul(size.width(), size.height());
}

static skgpu::ContextType BackendContextType(const std::string& backend) {
    if (backend == "gl") {
        return skgpu::ContextType::kGL;
    }
    if (backend == "grmtl") {
        return skgpu::ContextType::kMetal;
    }
    if (backend == "grvk") {
        return skgpu::ContextType::kVulkan;
    }
    return skgpu::ContextType::kMock;
}

static int EffectiveLimit(int runtimeLimit) {
    if (FLAGS_cullmax > 0) {
        return std::min(runtimeLimit, FLAGS_cullmax);
    }
    return runtimeLimit;
}

static SkISize ClampSize(SkISize size, int limit) {
    if (limit <= 0) {
        return size;
    }
    return {std::min(size.width(), limit), std::min(size.height(), limit)};
}

static sk_sp<SkSurface> MakeSurfaceForBackend(const std::string& backend,
                                              SkISize* size,
                                              std::unique_ptr<sk_gpu_test::GrContextFactory>* ganeshFactory,
                                              sk_gpu_test::ContextInfo* ganeshContextInfo,
                                              std::unique_ptr<skiatest::graphite::ContextFactory>* graphiteFactory,
                                              skiatest::graphite::ContextInfo* graphiteContextInfo,
                                              std::unique_ptr<skgpu::graphite::Recorder>* graphiteRecorder) {
    if (backend == "raster") {
        *size = ClampSize(*size, FLAGS_cullmax);
        return SkSurfaces::Raster(MakeImageInfo(*size));
    }

    if (backend == "gl") {
        *ganeshFactory = std::make_unique<sk_gpu_test::GrContextFactory>();
        *ganeshContextInfo = (*ganeshFactory)->getContextInfo(BackendContextType(backend));
        if (!ganeshContextInfo->directContext()) {
            return nullptr;
        }

        *size = ClampSize(*size, EffectiveLimit(ganeshContextInfo->directContext()->maxRenderTargetSize()));

        SkSurfaceProps props(0, kRGB_H_SkPixelGeometry);
        return SkSurfaces::RenderTarget(ganeshContextInfo->directContext(),
                                        skgpu::Budgeted::kNo,
                                        MakeImageInfo(*size),
                                        /*sampleCount=*/1,
                                        &props);
    }

    if (backend == "grmtl" || backend == "grvk") {
        *graphiteFactory = std::make_unique<skiatest::graphite::ContextFactory>(
                skiatest::graphite::TestOptions{});
        *graphiteContextInfo = (*graphiteFactory)->getContextInfo(BackendContextType(backend));
        if (!graphiteContextInfo->fContext) {
            return nullptr;
        }

        *graphiteRecorder = graphiteContextInfo->fContext->makeRecorder(
                ToolUtils::CreateTestingRecorderOptions());
        if (!*graphiteRecorder) {
            return nullptr;
        }

        *size = ClampSize(*size, EffectiveLimit(graphiteContextInfo->fContext->maxTextureSize()));

        return SkSurfaces::RenderTarget(graphiteRecorder->get(), MakeImageInfo(*size));
    }

    return nullptr;
}

static bool FlushSurfaceForBackend(const std::string& backend,
                                   sk_gpu_test::ContextInfo* ganeshContextInfo,
                                   skiatest::graphite::ContextInfo* graphiteContextInfo,
                                   std::unique_ptr<skgpu::graphite::Recorder>* graphiteRecorder) {
    if (backend == "raster") {
        return true;
    }

    if (backend == "gl") {
        if (!ganeshContextInfo->testContext() || !ganeshContextInfo->directContext()) {
            return false;
        }
        ganeshContextInfo->testContext()->flushAndSyncCpu(ganeshContextInfo->directContext());
        return true;
    }

    if (backend == "grmtl" || backend == "grvk") {
        if (!graphiteContextInfo->fTestContext || !graphiteContextInfo->fContext ||
            !*graphiteRecorder) {
            return false;
        }

        std::unique_ptr<skgpu::graphite::Recording> recording = (*graphiteRecorder)->snap();
        if (recording) {
            skgpu::graphite::InsertRecordingInfo info;
            info.fRecording = recording.get();
            graphiteContextInfo->fContext->insertRecording(info);
        }
        graphiteContextInfo->fTestContext->syncedSubmit(graphiteContextInfo->fContext);
        return true;
    }

    return false;
}

static bool RenderPictureToPngLikeDM(const sk_sp<SkPicture>& picture,
                                     const std::string& outputPath,
                                     const std::string& backend) {
    if (!picture) {
        return false;
    }

    SkISize size = DMViewportSize(picture);
    if (size.isEmpty()) {
        size = {1, 1};
    }
    std::unique_ptr<sk_gpu_test::GrContextFactory> ganeshFactory;
    sk_gpu_test::ContextInfo ganeshContextInfo;
    std::unique_ptr<skiatest::graphite::ContextFactory> graphiteFactory;
    skiatest::graphite::ContextInfo graphiteContextInfo;
    std::unique_ptr<skgpu::graphite::Recorder> graphiteRecorder;

    auto surface = MakeSurfaceForBackend(backend,
                                         &size,
                                         &ganeshFactory,
                                         &ganeshContextInfo,
                                         &graphiteFactory,
                                         &graphiteContextInfo,
                                         &graphiteRecorder);
    if (!surface) {
        ERROR("Failed to create a %s surface", backend.c_str());
        return false;
    }

    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->drawPicture(picture);

    if (!FlushSurfaceForBackend(
                backend, &ganeshContextInfo, &graphiteContextInfo, &graphiteRecorder)) {
        return false;
    }

    SkBitmap bitmap;
    if (!bitmap.tryAllocPixels(MakeImageInfo(size))) {
        return false;
    }
    if (!surface->readPixels(bitmap, 0, 0)) {
        return false;
    }

    SkPixmap pixmap;
    if (!bitmap.peekPixels(&pixmap)) {
        return false;
    }

    SkFILEWStream stream(outputPath.c_str());
    if (!stream.isValid()) {
        return false;
    }

    return SkPngEncoder::Encode(&stream, pixmap, {});
}

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    if (FLAGS_input.isEmpty()) {
        ERROR("Must specify --input");
        return 1;
    }

    sk_sp<SkPicture> picture = LoadPictureLikeDM(FLAGS_input[0]);
    if (!picture) {
        ERROR("Failed to parse picture from %s", FLAGS_input[0]);
        return 1;
    }

    sk_sp<SkPicture> finalPicture = MaybeOptimize(picture, FLAGS_transform[0], FLAGS_opt);
    if (!finalPicture) {
        ERROR("Failed to process picture from %s", FLAGS_input[0]);
        return 1;
    }

    if (!RenderPictureToPngLikeDM(finalPicture, FLAGS_output[0], FLAGS_backend[0])) {
        ERROR("Failed to write %s", FLAGS_output[0]);
        return 1;
    }

    return 0;
}
