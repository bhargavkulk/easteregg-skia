#include <algorithm>
#include <cstdio>
#include <string>

#include "include/core/SkBitmap.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkData.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkSamplingOptions.h"
#include "include/core/SkSerialProcs.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/encode/SkPngEncoder.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordPattern.h"
#include "src/core/SkRecords.h"
#include "src/image/SkImage_Base.h"
#include "tools/flags/CommandLineFlags.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "optimized.skp", "Output .skp file");

static sk_sp<SkPicture> PictureFromRecord(const SkRecord& records, const SkRect& bounds) {
    SkPictureRecorder recorder;
    SkCanvas* canvas = recorder.beginRecording(bounds);
    if (!canvas) {
        return nullptr;
    }
    SkRecordDraw(records, canvas, nullptr, nullptr, 0, nullptr, nullptr);
    return recorder.finishRecordingAsPicture();
}

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    if (FLAGS_input.isEmpty()) {
        ERROR("Must specify --input");
        return 1;
    }

    const std::string inputPath = FLAGS_input[0];
    const std::string outputPath = FLAGS_output[0];

    SkFILEStream input(inputPath.c_str());
    if (!input.isValid()) {
        ERROR("Failed to read file %s", inputPath.c_str());
        return 1;
    }

    sk_sp<SkPicture> picture = SkPicture::MakeFromStream(&input);
    if (!picture) {
        ERROR("Failed to deserialize SKP from %s", inputPath.c_str());
        return 1;
    }

    SkRect bounds(picture->cullRect());
    SkRecord records;
    SkRecordCanvas recorder(&records, bounds);
    picture->playback(&recorder);

    SkRecords::Is<SkRecords::SaveLayer> isSaveLayer;
    for (int i = 0; i < records.count(); ++i) {
        if (records.mutate(i, isSaveLayer)) {
            records.replace<SkRecords::Save>(i);
        }
    }

    sk_sp<SkPicture> optimizedPicture = PictureFromRecord(records, bounds);
    if (!optimizedPicture) {
        ERROR("Failed to rebuild optimized picture");
        return 1;
    }

    SkFILEWStream output(outputPath.c_str());
    if (!output.isValid()) {
        ERROR("Failed to open output file %s", outputPath.c_str());
        return 1;
    }

    SkSerialProcs serialProcs;
    serialProcs.fImageProc = [](SkImage* image, void*) -> sk_sp<SkData> {
        auto options = SkPngEncoder::Options{};
        auto direct = as_IB(image)->directContext();
        if (sk_sp<SkData> data = SkPngEncoder::Encode(direct, image, options)) {
            return data;
        }

        sk_sp<SkImage> nonTexture = image->makeNonTextureImage(direct);
        if (nonTexture) {
            if (sk_sp<SkData> data = SkPngEncoder::Encode(direct, nonTexture.get(), options)) {
                return data;
            }
        }

        nonTexture = image->makeNonTextureImage(nullptr);
        if (nonTexture) {
            if (sk_sp<SkData> data = SkPngEncoder::Encode(nullptr, nonTexture.get(), options)) {
                return data;
            }
        }

        sk_sp<SkImage> raster = image->makeRasterImage(direct);
        if (raster) {
            if (sk_sp<SkData> data = SkPngEncoder::Encode(nullptr, raster.get(), options)) {
                return data;
            }
        }

        raster = image->makeRasterImage(nullptr);
        if (raster) {
            if (sk_sp<SkData> data = SkPngEncoder::Encode(nullptr, raster.get(), options)) {
                return data;
            }
        }

        SkBitmap bitmap;
        if (as_IB(image)->getROPixels(direct, &bitmap)) {
            if (sk_sp<SkData> data = SkPngEncoder::Encode(bitmap.pixmap(), options)) {
                return data;
            }
        }

        bitmap.reset();
        if (as_IB(image)->getROPixels(nullptr, &bitmap)) {
            if (sk_sp<SkData> data = SkPngEncoder::Encode(bitmap.pixmap(), options)) {
                return data;
            }
        }

        bitmap.reset();
        if (image->asLegacyBitmap(&bitmap)) {
            if (sk_sp<SkData> data = SkPngEncoder::Encode(bitmap.pixmap(), options)) {
                return data;
            }
        }

        auto surface = SkSurfaces::Raster(
                SkImageInfo::MakeN32Premul(std::max(image->width(), 1), std::max(image->height(), 1)));
        if (surface) {
            surface->getCanvas()->clear(SK_ColorTRANSPARENT);
            surface->getCanvas()->drawImage(image, 0, 0, SkSamplingOptions());
            sk_sp<SkImage> snapshot = surface->makeImageSnapshot();
            if (snapshot) {
                if (sk_sp<SkData> data = SkPngEncoder::Encode(nullptr, snapshot.get(), options)) {
                    return data;
                }
                bitmap.reset();
                if (as_IB(snapshot.get())->getROPixels(nullptr, &bitmap)) {
                    if (sk_sp<SkData> data = SkPngEncoder::Encode(bitmap.pixmap(), options)) {
                        return data;
                    }
                }
            }
        }

        return nullptr;
    };

    optimizedPicture->serialize(&output, &serialProcs);
    return 0;
}
