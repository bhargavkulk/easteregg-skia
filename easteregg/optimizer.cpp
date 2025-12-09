#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include "easteregg/easteregg.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkPicture.h"
#include "include/core/SkPictureRecorder.h"
#include "include/core/SkStream.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "src/core/SkRecordDraw.h"
#include "src/core/SkRecordOpts.h"
#include "tools/flags/CommandLineFlags.h"

#ifdef DEBUG
#define DPRINT(x) std::cout << x << std::endl
#else
#define DPRINT(x)
#endif

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "optimized.skp", "Output .skp file");
static DEFINE_string(transform, "easteregg", "Transform to run: easteregg, skrecordopt, or none");

struct RecordPrinter {
    std::ostringstream os;
    int index = 0;

    template <typename T> void operator()(const T& op) {
        os << "    [" << index++ << "] " << typeid(T).name() << "<br />\n";
    }

    std::string str() { return os.str(); }
};

sk_sp<SkPicture> PictureFromRecord(const SkRecord& records, const SkRect& bounds) {
    SkPictureRecorder recorder;
    SkCanvas* canvas = recorder.beginRecording(bounds);
    if (!canvas) {
        return nullptr;
    }
    SkRecordDraw(records, canvas, nullptr, nullptr, 0, nullptr, nullptr);
    return recorder.finishRecordingAsPicture();
}

bool writePictureToSkp(const sk_sp<SkPicture>& picture, const std::string& path) {
    if (!picture) {
        return false;
    }
    SkFILEWStream stream(path.c_str());
    if (!stream.isValid()) return false;
    picture->serialize(&stream);
    return true;
}

int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    if (FLAGS_input.isEmpty()) {
        ERROR("Must specify --input");
        return 1;
    }

    SkFILEStream stream(FLAGS_input[0]);
    if (!stream.isValid()) {
        ERROR("Failed to read file %s", FLAGS_input[0]);
        return 1;
    }

    const std::string outputPath = FLAGS_output[0];

    sk_sp<SkPicture> picture(SkPicture::MakeFromStream(&stream));
    if (!picture) {
        ERROR("Error loading skp from %s", FLAGS_input[0]);
        return 1;
    }

    SkRect bounds(picture->cullRect());
    SkRecord records;
    SkRecordCanvas recorder(&records, bounds);

    picture->playback(&recorder);

    DPRINT("Record has " << records.count() << " commands.");

    const std::string transform = FLAGS_transform[0];

    if (transform == "easteregg") {
        RemoveOpaqueSaveLayers opt;
        opt.transform(records);

        auto optimizedPicture = PictureFromRecord(records, bounds);
        if (!writePictureToSkp(optimizedPicture, outputPath)) {
            ERROR("Failed to write %s", outputPath.c_str());
            return 1;
        }
    } else if (transform == "skrecordopt") {
        SkRecordOptimize(&records);

        auto optimizedPicture = PictureFromRecord(records, bounds);
        if (!writePictureToSkp(optimizedPicture, outputPath)) {
            ERROR("Failed to write %s", outputPath.c_str());
            return 1;
        }
    } else if (transform == "none") {
        if (!writePictureToSkp(picture, outputPath)) {
            ERROR("Failed to write %s", outputPath.c_str());
            return 1;
        }
    } else {
        ERROR("Unknown transform '%s'", transform.c_str());
        return 1;
    }

    return 0;
}
