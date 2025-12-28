from sys import argv

import skia

picture = skia.Picture.MakeFromStream(skia.FILEStream(argv[1]))
if not picture:
    print('Bad skp file')
else:
    bounds = picture.cullRect().roundOut()
    size = bounds.size()
    print(f'{size.width()},{size.height()}')
