Kleiderbügel
============

# Creating content

## Requirements

First you need `exiftool`:

```
brew install exiftool
```

## Remove all EXIF tags

(You may first want to rename the files to match the suffix as created by the camera)

```
exiftool -all= *.jpg
```

**Note:** If the image has been rotated just using metadata, this information will be lost!

## Create and compress PNG images

### Install PNG compressor

```
brew install zopfli
```

### Convert from Photoshop

```
find . -name '*.psd' -exec convert {} {}.png \;
