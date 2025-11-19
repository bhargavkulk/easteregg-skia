#include <cstdio>
#include "include/core/SkCanvas.h"
#include "include/core/SkImage.h"
#include "include/core/SkPicture.h"
#include "include/core/SkStream.h"
#include "src/core/SkRecord.h"
#include "src/core/SkRecordCanvas.h"
#include "tools/flags/CommandLineFlags.h"

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file");
static DEFINE_string(output, "index.html", "Output LOG file");

struct RecordPrinter {
    FILE* file;
    int index = 0;

    RecordPrinter(FILE* file) : file(file) {}

    template <typename T> void operator()(const T& op) {
        fprintf(file, "    [%d] %s\n", index++, typeid(T).name());
    }
};

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
    SkRecordCanvas recorder(&records, bounds);

    picture->playback(&recorder);

    printf("Record has %d commands.\n\n", records.count());

    FILE* outFile = fopen(FLAGS_output[0], "w");
    if (!outFile) {
        ERROR("Failed to open output file %s", FLAGS_output[0]);
        return 1;
    }

    RecordPrinter printer(outFile);
    for (int i = 0; i < records.count(); i++) {
        records.visit(i, printer);
    }

    fclose(outFile);

    return 0;
}
