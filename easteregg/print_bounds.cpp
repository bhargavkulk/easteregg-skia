#include <iostream>
#include "include/core/SkPicture.h"
#include "include/core/SkSize.h"
#include "include/core/SkStream.h"

int main(int argc, char** argv) {
    if (argc < 2) {
        SkDebugf("Usage:\n  %s SKP_FILE [DATA_URL]\n", argv[0]);
        return 1;
    }
    SkFILEStream input(argv[1]);
    if (!input.isValid()) {
        SkDebugf("Bad file: '%s'\n", argv[1]);
        return 2;
    }
    sk_sp<SkPicture> pic = SkPicture::MakeFromStream(&input);
    if (!pic) {
        SkDebugf("Bad skp: '%s'\n", argv[1]);
        return 3;
    }
    SkISize size = pic->cullRect().roundOut().size();
    std::cout << size.width() << ',' << size.height() << std::endl;
}
