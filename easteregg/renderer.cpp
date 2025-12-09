#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>

#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkImage.h"
#include "include/core/SkPicture.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/encode/SkPngEncoder.h"
#include "tools/flags/CommandLineFlags.h"

#ifdef DEBUG
#define DPRINT(x) std::cout << x << std::endl
#else
#define DPRINT(x)
#endif

#define ERROR(fmt, ...) fprintf(stderr, "Error: " fmt "\n", ##__VA_ARGS__)

static DEFINE_string(input, "", "Input .skp file to render");
static DEFINE_string(output, "output.png", "Output .png file path");

bool RenderPictureToPng(const sk_sp<SkPicture>& picture, const std::string& outputPath) {
    if (!picture) {
        return false;
    }

    SkRect bounds = picture->cullRect();
    SkIRect intBounds = bounds.roundOut();
    if (intBounds.isEmpty()) {
        intBounds = SkIRect::MakeWH(1, 1);
    }

    auto surface = SkSurfaces::Raster(
            SkImageInfo::MakeN32Premul(intBounds.width(), intBounds.height()));
    if (!surface) {
        return false;
    }

    SkCanvas* canvas = surface->getCanvas();
    canvas->clear(SK_ColorTRANSPARENT);
    canvas->translate(-bounds.left(), -bounds.top());
    picture->playback(canvas);

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

    SkFILEStream stream(FLAGS_input[0]);
    if (!stream.isValid()) {
        ERROR("Failed to read file %s", FLAGS_input[0]);
        return 1;
    }

    sk_sp<SkPicture> picture(SkPicture::MakeFromStream(&stream));
    if (!picture) {
        ERROR("Failed to parse picture from %s", FLAGS_input[0]);
        return 1;
    }

    const std::string outputPath = FLAGS_output[0];
    if (!RenderPictureToPng(picture, outputPath)) {
        ERROR("Failed to write %s", outputPath.c_str());
        return 1;
    }

    DPRINT("Rendered " << FLAGS_input[0] << " to " << outputPath);
    return 0;
}
