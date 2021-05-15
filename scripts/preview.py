#!/usr/bin/env python

import os, io, re, yaml, toml
from termcolor import cprint
from PIL import Image, ImageFont, ImageDraw
import xml.etree.ElementTree as ET
from pathlib import Path


configFile = "./config/_default/config.toml"
contentPath = "./content"
filePattern = "(_?)index(\.([a-zA-Z-]){2,5})?\.md"

namespaces = {"svg": "http://www.w3.org/2000/svg", "xlink": "http://www.w3.org/1999/xlink"}

def loadConfig(configFile):
    config = toml.load(configFile)
    return config["params"]["preview"]

def readMetadata (file):
    post = io.open(file, mode="r", encoding="utf-8").read()
    header = re.sub(r'^---$.(.*?)^---$.*', "\\1", post, 0, re.MULTILINE | re.DOTALL)
    try:
        post = yaml.load(header, Loader=yaml.FullLoader)
    except yaml.YAMLError as exc:
        if hasattr(exc, 'problem_mark'):
           mark = exc.problem_mark
           cprint("Error in {} position: ({}:{})".format(file, mark.line + 1, mark.column + 1), 'red')
    except Exception as inst:
        cprint("Error in %s".format(file), 'red')

    return post

def drawTitle(title, file, config):
    font = ImageFont.truetype(config["font"]["location"], config["font"]["size"])
    img = Image.new('RGBA', (config["size"]["width"], config["size"]["height"]), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = draw.textsize(title)
    draw.text((15,15), title, fill=config["font"]["color"], font=font)
    img.save(file)

def drawSVG(title, previewImg, outFile, config):
    global namespaces
    template = config["svg"]["template"]
    templateBase = os.path.dirname(template)
    # Python has an incomplete XML implementation :( https://stackoverflow.com/questions/44282975/how-to-access-attribute-value-in-xml-containing-namespace-using-elementtree-in-p
    xlinkAttr = "{" + namespaces["xlink"] + "}" + "href"

    svgTree = ET.parse(template)

    # Set paths relative to output dir
    for styleElem in svgTree.findall("//svg:style", namespaces):
        style = styleElem.text
        for urlMatch, url in re.findall(r'(url\s*?\([\'\"]?(.*?)[\'\"]?\))', style, re.S | re.M):
            relLocation = os.path.normpath(os.path.join(templateBase, os.path.dirname(url)))
            targetPath = os.path.relpath(relLocation, os.path.dirname(outFile))
            newLocation = os.path.join(targetPath, os.path.basename(url))
            style = style.replace(urlMatch, "url('" + newLocation + "')")
        styleElem.text = style

    for linkElem in svgTree.findall("//*[@xlink:href]", namespaces):
        link = linkElem.get(xlinkAttr)
        relLocation = os.path.normpath(os.path.join(templateBase, os.path.dirname(link)))
        targetPath = os.path.relpath(relLocation, os.path.dirname(outFile))
        newLocation = os.path.join(targetPath, os.path.basename(link))
        linkElem.set(xlinkAttr, newLocation)

    # Update image
    previewImg = os.path.join(os.path.relpath(os.path.dirname(outFile), os.path.dirname(previewImg)), os.path.basename(previewImg))
    svgTree.findall("//*[@id = 'hanger']", namespaces)[0].set(xlinkAttr, previewImg)

    # Update text
    # /svg:tspan
    svgTree.findall("//*[@id = 'text-container']", namespaces)[0].text = title

    cprint("Writing {}".format(outFile), 'green')
    svgTree.write(outFile)

def drawPNG(title, file, config):
    drawTitle(title, output, config)

def getPreviewImg(config, contentFile):
    if config["source"] == "file":
        path = os.path.dirname(contentFile)
        return os.path.join(path, config["image"])
    elif config["source"] == "post":
        metadata = readMetadata(contentFile)
        raise NotImplementedError

config = loadConfig(open(configFile, 'r'))

for subdir, dirs, files in os.walk(contentPath):
    for file in files:
        if re.match(filePattern, file):
            cprint("Processing " + os.path.join(subdir, file), 'green')
            contentFile = os.path.join(subdir, file)
            metadata = readMetadata(contentFile)

            previewImg = getPreviewImg(config, contentFile)
            if config["format"] == "svg":
                output = os.path.join(subdir, config["outputPrefix"] + ".svg")
                drawSVG(metadata["title"], previewImg, output, config)
            #elif config["format"] == "png":
            #    drawPNG(metadata["title"], output, config)
