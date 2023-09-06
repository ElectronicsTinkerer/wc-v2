
import os
import urllib.parse
import re


class SP:  # [S]yntax[P]roperties
    def __init__(self, filenum, delimiter, del_per_line, mode, need_newline, template_arg_modifier):
        self.filenum = filenum
        self.delimiter = delimiter
        self.dpl = del_per_line
        self.mode = mode
        self.neednl = need_newline
        self.template_arg_modifier = template_arg_modifier

class MODE:
    def __init__(self, begin, end, strip_whitespace, retain, do_escape):
        self.begin = begin
        self.end = end
        self.stripws = strip_whitespace
        self.retain = retain
        self.do_escape = do_escape

class Template:
    def __init__(self, filename, filenum, contents):
        self.filename = filename
        self.filenum = filenum
        self.contents = contents

class ZWCFile:
    def __init__(self, filebase, fileext, title):
        self.filebase = filebase
        self.fileext = fileext
        self.title = title

    def __lt__(self, other):
        return self.title.lower() < other.title.lower()

    def __eq__(self, other):
        return self.title.lower() == other.title.lower()

TEMPLATEDIR = "templates"
INDIR  = "rawpages"
OUTDIR = "genpages"
INDEXZWC = "index.zwc"
INDEXIGNORE = ".indexignore"

def sp_image_linker(link):
    delim_index = link.rfind("/")
    return f"{link[:delim_index+1]}s_{link[delim_index+1:]}"

SYNTXLUT = { # Filetype number, delimiter, delimiters per line, mode type, needs newline after template, modified parameter function
    "```"  : SP(500, "",  0, "code", False, None),   # CODE BLOCK TOGGLE
    "# "   : SP(501, "",  0, "none", True,  None),   # HEADING 1
    "## "  : SP(502, "",  0, "none", True,  None),   # HEADING 2
    "### " : SP(503, "",  0, "none", True,  None),   # HEADING 3
    "=>"   : SP(504, " ", 1, "none", True,  None),   # HYPERLINK
    "* "   : SP(505, "",  0, "list", False, None),   # LIST ELEMENT
    "> "   : SP(506, "",  0, "none", False, None),   # BLOCKQUOTE
    "! "   : SP(507, " ", 1, "none", True,  None),   # IMAGE
    "!! "  : SP(508, " ", 1, "none", True,  sp_image_linker),     # IMAGE (with scaled link - full size is linked)
    "<@>"  : SP(509, "",  0, "html", False, None)   # HTML BLOCK TOGGLE
}
MODES = { #       BEGIN      END         STRIP  RETAIN ESCAPE
    "none" : MODE("",        "",         True,  False, True),
    "code" : MODE("<pre>\n", "</pre>\n", False, True,  True),
    "html" : MODE("",        "",         True,  True,  False),
    "list" : MODE("<ul>",    "</ul>",    True,  False, True)
}


# https://security.stackexchange.com/questions/66252/encodeuricomponent-in-a-unquoted-html-attribute
# Enocdes string to use HTML instead of raw characters
# Param: string: the string to be HTML encoded (using the HTML entities)
def encodehtml(string):
        return (string.replace("&", "&amp;")
                .replace("\"", "&quot;")
                .replace("'", "&#39;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("—", "&mdash;")
            )


# Encodes a string to use URL encoding instead of raw characters
def encodeurl(string):
    return urllib.parse.quote(string, safe="/:", encoding="utf-8")


# Reads a template string and fills in the template_args where TEMPLATEARGCHARs are found
def readtemplate(template, template_args, template_arg_modifier=None):
    tem_string = ""
    arg = 0

    for line in template.contents.split('\n'):
        line.strip()

        # URL based on previous template arg
        if line.startswith("%%="):
            if arg == 0:
                print(f"[WARN] Template {template.filenum} has modified URL as first parameter")
                continue

            try:
                if template_arg_modifier:
                    tam = template_arg_modifier(template_args[arg-1])
                    tem_string += encodeurl(tam)
                else:
                    tem_string += encodeurl(template_args[arg-1])
            except:
                print(f"[WARN] Template {template.filenum} has unsatisfied modified URL parameter")

        # HTML text based on previous template arg
        elif line.startswith("%%"):
            if arg == 0:
                print(f"[WARN] Template {template.filenum} has modified HTML as first parameter")
                continue

            try:
                if template_arg_modifier:
                    tam = template_arg_modifier(template_args[arg-1])
                    tem_string += encodeurl(tam)
                else:
                    tem_string += encodehtml(template_args[arg-1])
            except:
                print(f"[WARN] Template {template.filenum} has unsatisfied modified HTML parameter")

        # URL
        elif line.startswith("%="):
            try:
                tem_string += encodeurl(template_args[arg])
            except:
                print(f"[WARN] Template {template.filenum} has unsatisfied URL parameter")
            finally:
                arg += 1

        # HTML text
        elif line.startswith("%"):
            try:
                tem_string += encodehtml(template_args[arg])
            except:
                print(f"[WARN] Template {template.filenum} has unsatisfied HTML argument")
            finally:
                arg += 1

        else:
            tem_string += line

    return tem_string


# Reads the .zwc file and creates the HTML for the text
def generatecontent(zwc_file, templates):

    mode = "none"

    contents = '\n<div id="content" class="container">'

    for line in zwc_file.readlines():
        linestrip = line
        linestrip.strip()
        linestrip = linestrip.replace("\n", "") # This keeps leading whitespace!
        marked = False
        for marker, info in SYNTXLUT.items():
            if linestrip.startswith(marker):
                marked = True
                elif_extension = True
                if mode != info.mode and not MODES[mode].retain:
                    contents += MODES[mode].end
                    mode = info.mode
                    contents += MODES[mode].begin
                    elif_extension = False

                if MODES[mode].stripws:
                    line = linestrip
                line = line[len(marker):]
                try:
                    contents += readtemplate(templates[info.filenum], line.split(maxsplit=info.dpl), info.template_arg_modifier)
                except KeyError:
                    print(f"[WARN] Encountered template id {info.filenum} with no associated template file")
                if info.neednl:
                    contents += "\n"

                if elif_extension and mode == info.mode and MODES[mode].retain:
                    contents += MODES[mode].end
                    mode = "none"
                    contents += MODES[mode].begin
        
        if not marked:
            if not MODES[mode].retain:
                contents += MODES[mode].end
                mode = "none"

            l2e = line
            if MODES[mode].stripws and linestrip != "":
                l2e = linestrip

            # Only escape HTML characters if in a mode that requires escape sequences
            if MODES[mode].do_escape:
                contents += encodehtml(l2e) + "\n"
            else:
                contents += l2e

    if mode != "none":
        contents += MODES[mode].end
        
    contents += "</div>\n"

    return contents


# Generates the HTML for the entire page (except that determined by the .zwc file)
def generatepage(file, templates):
    print(f"[INFO] Reading {file}")

    page_string = ""

    page_title = file

    zwc = open(file, "r")
    for line in zwc.readlines():
        line.strip()
        if line.startswith("# "):
            page_title = line[2:].replace("\n", "")
            zwc.seek(0, 0)
            break

    found_500 = False
    head_complete = False    # For HEAD and BODY

    for temnum, temval in templates.items():
        
        if temnum == 0:
            page_string += temval.contents + "\n<head>\n"
        elif (temnum >= 1 and temnum < 90):
            page_string += temval.contents
        elif temnum == 90:   # Title
            page_string += readtemplate(temval, [page_title])
        elif (temnum >= 91 and temnum < 100):
            page_string += temval.contents
        elif temnum >= 100 and temnum < 200:
            print("[WARN] File includes are not currently supported")
        elif temnum >= 200 and temnum < 300:
            if not head_complete:
                head_complete = True
                page_string += "\n</head>\n<body>\n"
            page_string += temval.contents
        elif temnum >= 500 and temnum < 600:
            if not found_500:
                page_string += generatecontent(zwc, templates)
            found_500 = True
        elif temnum >= 800 and temnum < 900:
            page_string += temval.contents
        elif temnum == 999:
            page_string += "\n</body>\n"
            page_string += temval.contents
        else:
            print(f"[WARN] Filetype number {temnum} is unused")

    return page_string, page_title


def generateallpages(in_files):
    index_list = []
    total_pages = 0

    for filename in in_files:
        filebase, fileext = os.path.splitext(filename)
        file = os.path.join(INDIR, filebase + fileext)
        # If file is a regular file (not a folder), generate a page with it
        if os.path.isfile(file) and fileext == ".zwc":
            file_contents, file_title = generatepage(file, templates)
            index_list.append(ZWCFile(filebase, fileext, file_title))
            file_to_write = os.path.join(OUTDIR, filebase + ".html")
            try:
                with open(file_to_write, "w") as genfile:
                    genfile.write(file_contents)
                total_pages += 1
            except:
                print("[ERROR] Unable to write to " + file_to_write)
                exit(-1)

    return index_list, total_pages


if __name__ == "__main__":

    try:
        os.mkdir(OUTDIR)
        print("[INFO] Created output directory")
    except FileExistsError:
        print("[INFO] Output directory exists")
        

    templates = {}
    template_listing = os.listdir(TEMPLATEDIR)
    template_listing.sort()
    for filename in template_listing:
        file = os.path.join(TEMPLATEDIR, filename)

        # Extract the template number from the file name
        match = re.search(r"^0*([0-9]+)_", filename)
        if not match or not match.group(1):
            print(f"[WARN] Ignoring template {filename} due to invalid filename")
            continue

        filenum = int(match.group(1), base=10)

        # If file is a regular file (not a folder), generate a page with it
        filebase, fileextention = os.path.splitext(filename)
        if os.path.isfile(file) and fileextention == ".html":
            with open(file, "r") as f:
                templates.update( {
                    filenum : Template(filename, filenum, f.read())
                } )

    # Remove the index file
    index_file = os.path.join(INDIR, INDEXZWC)
    try:
        os.remove(index_file)
    except:
        print(f"[INFO] No previous {index_file} file detected")
    
    index_list, total_pages = generateallpages(os.listdir(INDIR))

    index_list.sort()

    indexignore = [];
    try:
        with open(os.path.join(INDIR, INDEXIGNORE)) as indexignore_file:
            indexignore = indexignore_file.read().split('\n');
    except:
        print("[WARN] Unable to open index ignore file")

    try:
        with open(index_file, "w") as indexfile:
            indexfile.write("# Index\n")
            for element in index_list:
                if element.filebase not in indexignore:
                    indexfile.write(f"=> {element.filebase}.html {element.title}\n")
    except:
        print("[WARN] Unable to generate index file")

    index_list, pages = generateallpages([INDEXZWC])
    total_pages += pages

    print(f"[INFO] DONE! Total pages {total_pages}")
