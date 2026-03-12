#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>

#include "easteregg/easteregg.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkData.h"
#include "include/core/SkFontMgr.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkSerialProcs.h"
#include "include/core/SkStream.h"
#include "include/core/SkTypeface.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordOpts.h"
#include "tools/flags/CommandLineFlags.h"
#include "tools/fonts/FontToolUtils.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output_dir, "opt_pass_dumps", "Base output directory; each input writes to <output_dir>/<skp_name>/");
static DEFINE_string(output_base, "",
                     "Optional output base name. Defaults to input filename stem.");
static DEFINE_string(transform, "easteregg", "Transform pipeline to run: easteregg, skrecordopt, or none");

static sk_sp<SkData> SerializeTypefaceWithData(SkTypeface* typeface, void*) {
    if (!typeface) {
        return nullptr;
    }
    return typeface->serialize(SkTypeface::SerializeBehavior::kDoIncludeData);
}

static sk_sp<SkImage> DeserializeImageLikeDM(const void* data, size_t size, void*) {
    sk_sp<SkData> tmpData = SkData::MakeWithoutCopy(data, size);
    sk_sp<SkImage> image = SkImages::DeferredFromEncodedData(std::move(tmpData));
    return image ? image->makeRasterImage(nullptr) : nullptr;
}

static sk_sp<SkTypeface> DeserializeTypefaceLikeDM(const void* data, size_t, void*) {
    if (!data) {
        return nullptr;
    }

    SkStream** stream = reinterpret_cast<SkStream**>(const_cast<void*>(data));
    return SkTypeface::MakeDeserialize(*stream, ToolUtils::TestFontMgr());
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

static bool writePictureToSkp(const sk_sp<SkPicture>& picture, const std::filesystem::path& path) {
    if (!picture) {
        return false;
    }
    SkFILEWStream stream(path.string().c_str());
    if (!stream.isValid()) {
        return false;
    }

    SkSerialProcs serialProcs;
    serialProcs.fTypefaceProc = SerializeTypefaceWithData;
    picture->serialize(&stream, &serialProcs);
    return true;
}

static std::string TwoDigitIndex(int index) {
    char buf[16];
    std::snprintf(buf, sizeof(buf), "%02d", index);
    return std::string(buf);
}

static bool DumpPass(const SkRecord& records, const SkRect& bounds,
                     const std::filesystem::path& outputBaseDir, const std::string& outputBase,
                     int passIndex) {
    const std::filesystem::path skpDir = outputBaseDir / outputBase;
    std::error_code ec;
    std::filesystem::create_directories(skpDir, ec);
    if (ec) {
        ERROR("Failed to create output dir %s: %s", skpDir.string().c_str(), ec.message().c_str());
        return false;
    }

    const std::string fileName = outputBase + "." + TwoDigitIndex(passIndex) + ".skp";
    const std::filesystem::path outputPath = skpDir / fileName;

    sk_sp<SkPicture> picture = PictureFromRecord(records, bounds);
    if (!picture) {
        ERROR("Failed to materialize picture after pass %d", passIndex);
        return false;
    }

    if (!writePictureToSkp(picture, outputPath)) {
        ERROR("Failed to write %s", outputPath.string().c_str());
        return false;
    }

    printf("%s\n", outputPath.string().c_str());
    return true;
}

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    if (FLAGS_input.isEmpty()) {
        ERROR("Must specify --input");
        return 1;
    }

    std::filesystem::path outputDir = FLAGS_output_dir[0];
    std::error_code ec;
    std::filesystem::create_directories(outputDir, ec);
    if (ec) {
        ERROR("Failed to create output dir %s: %s", outputDir.string().c_str(),
              ec.message().c_str());
        return 1;
    }

    SkFILEStream stream(FLAGS_input[0]);
    if (!stream.isValid()) {
        ERROR("Failed to read file %s", FLAGS_input[0]);
        return 1;
    }

    SkDeserialProcs deserialProcs;
    deserialProcs.fImageProc = DeserializeImageLikeDM;
    deserialProcs.fTypefaceProc = DeserializeTypefaceLikeDM;

    sk_sp<SkPicture> picture(SkPicture::MakeFromStream(&stream, &deserialProcs));
    if (!picture) {
        ERROR("Error loading skp from %s", FLAGS_input[0]);
        return 1;
    }

    const std::string transform = FLAGS_transform[0];
    std::string outputBase;
    if (!FLAGS_output_base.isEmpty()) {
        outputBase = FLAGS_output_base[0];
    }
    if (outputBase.empty()) {
        outputBase = std::filesystem::path(FLAGS_input[0]).stem().string();
        if (outputBase.empty()) {
            outputBase = "snapshot";
        }
    }

    SkRect bounds(picture->cullRect());
    SkRecord records;
    SkRecordCanvas recorder(&records, bounds);
    picture->playback(&recorder);

    int passIndex = 1;

    if (transform == "none") {
        if (!DumpPass(records, bounds, outputDir, outputBase, passIndex)) {
            return 1;
        }
    } else if (transform == "skrecordopt") {
        SkRecordOptimize(&records);
        if (!DumpPass(records, bounds, outputDir, outputBase, passIndex)) {
            return 1;
        }
    } else if (transform == "easteregg") {
        GradientDstInToMasks opt3;
        RemoveLoneLuma opt2;
        DstInToClip opt4;
        NewRemoveOpaqueSaveLayers opt1;
        // CopyRemoveOpaqueSaveLayer opt1;

        // Pass number mapping for --transform=easteregg:
        //   01 -> GradientDstInToMasks
        //   02 -> RemoveLoneLuma
        //   03 -> DstInToClip
        //   04 -> NewRemoveOpaqueSaveLayers
        opt3.transform(&records);
        if (!DumpPass(records, bounds, outputDir, outputBase, passIndex++)) {
            return 1;
        }

        opt2.transform(&records);
        if (!DumpPass(records, bounds, outputDir, outputBase, passIndex++)) {
            return 1;
        }

        opt4.transform(&records);
        if (!DumpPass(records, bounds, outputDir, outputBase, passIndex++)) {
            return 1;
        }

        opt1.transform(&records);
        if (!DumpPass(records, bounds, outputDir, outputBase, passIndex++)) {
            return 1;
        }
    } else {
        ERROR("Unknown transform '%s' (expected easteregg, skrecordopt, or none)", transform.c_str());
        return 1;
    }

    return 0;
}
