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

A better solution which keeps the ICC profile would be, [see](https://exiftool.org/forum/index.php?topic=2829.0):
```
exiftool -all= -tagsfromfile @ -icc_profile FILE
```

**Note:** If the image has been rotated just using metadata, this information will be lost!

## Create and compress PNG images

### Install PNG compressor

```
brew install zopfli
```

### Convert from Photoshop

```
find . -name '*.psd' -print -exec convert {} {}.png \;
find . -name '*-0.png' -print -exec zopflipng -m {} {}-c.png \;
```

# Redirects

The canonical name is [https://kleiderbügel.blaufusstölpel.de](kleiderbügel.blaufusstölpel.de) or `xn--kleiderbgel-0hb.xn--blaufusstlpel-qmb.de`.

See also [IDN-Web-Converter](https://www.denic.de/service/tools/idn-web-converter/)

| IDN URL                         | URL                                           | Repository             |
|---------------------------------|-----------------------------------------------|------------------------|
| kleiderbügel.blaufußtölpel.de   | xn--kleiderbgel-0hb.xn--blaufutlpel-06a41a.de | xn--kleiderbgel-06a41a |
| kleiderbuegel.blaufußtölpel.de  | kleiderbuegel.xn--blaufutlpel-06a41a.de       | kleiderbuegel-06a41a   |
| kleiderbuegel.blaufusstölpel.de | kleiderbuegel.xn--blaufusstlpel-qmb.de        | kleiderbuegel-qmb      |


# Debugging `static` mounts

```
/usr/local/bin/hugo server -D -F --debug --disableFastRender --renderToDisk
```

# Date series generator
https://onlinetools.com/time/generate-date-sequence


# Data encoding

Due to confusion on how to encode double sided hangers, this is the right way:

For hangers with two identical sides use:
```yaml
params:
    doublesided: true
```

For hangers with two different sides with two images use the tags "Beidseitig"

```yaml
tags:
    - Beidseitig
```