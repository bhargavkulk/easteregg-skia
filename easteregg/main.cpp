#include <cstdio>
#include "include/core/SkCanvas.h"
#include "include/core/SkImage.h"
#include "include/core/SkPicture.h"
#include "include/core/SkRecorder.h"
#include "include/core/SkStream.h"
#include "src/core/SkRecord.h"
#include "tools/flags/CommandLineFlags.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "output.png", "Output PNG file");

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

    sk_sp<SkPicture> picture(SkPicture::MakeFromStream(&stream));
    if (!picture) {
        ERROR("Error loading skp from %s", FLAGS_input[0]);
        return 1;
    }

    SkRect bounds(picture->cullRect());
    SkRecord records;
    SkRecorder recorder(&records, bounds.width(), bounds.height());
    picture->playback(&recorder);

    printf("Record has %d commands.\n", records.count());

    return 0;
}
