#include <cstdio>
#include <cstdlib>
#include <string>

#include "easteregg/easteregg.h"
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
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordOpts.h"
#include "tools/flags/CommandLineFlags.h"
#include "tools/fonts/FontToolUtils.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "output.png", "Output .png file path");
static DEFINE_bool(opt, false, "Apply optimizer transforms before rendering");
static DEFINE_string(transform, "easteregg",
                     "Transform to run when --opt=true: easteregg, skrecordopt, or none");
static DEFINE_int(skpViewportSize, 1000,
                  "Width & height of the viewport used to crop skp rendering (DM behavior).");

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
    SkRect viewport = picture->cullRect();
    if (!viewport.intersect(SkRect::MakeWH(FLAGS_skpViewportSize, FLAGS_skpViewportSize))) {
        return {0, 0};
    }
    return viewport.roundOut().size();
}

static bool RenderPictureToPngLikeDM(const sk_sp<SkPicture>& picture, const std::string& outputPath) {
    if (!picture) {
        return false;
    }

    SkISize size = DMViewportSize(picture);
    if (size.isEmpty()) {
        size = {1, 1};
    }

    auto surface = SkSurfaces::Raster(SkImageInfo::MakeN32Premul(size.width(), size.height()));
    if (!surface) {
        return false;
    }

    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->clipRect(SkRect::MakeWH(FLAGS_skpViewportSize, FLAGS_skpViewportSize));
    canvas->drawPicture(picture);

    sk_sp<SkImage> image = surface->makeImageSnapshot();
    if (!image) {
        return false;
    }

    SkPixmap pixmap;
    if (!image->peekPixels(&pixmap)) {
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

    if (!RenderPictureToPngLikeDM(finalPicture, FLAGS_output[0])) {
        ERROR("Failed to write %s", FLAGS_output[0]);
        return 1;
    }

    return 0;
}
