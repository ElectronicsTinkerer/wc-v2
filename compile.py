#!/usr/bin/python3

import os
import sys
import getopt
import urllib.parse
import re
import tomllib

# Formatters for code
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound


class SP:  # [S]yntax[P]roperties
    def __init__(self, filenum, delimiter, del_per_line, mode, need_newline, template_arg_modifier):
        self.filenum = filenum
        self.delimiter = delimiter
        self.dpl = del_per_line
        self.mode = mode
        self.neednl = need_newline
        self.template_arg_modifier = template_arg_modifier

class MODE:
    def __init__(self, begin, end, strip_whitespace, retain, do_escape, block_mode_processor):
        self.begin = begin
        self.end = end
        self.stripws = strip_whitespace
        self.retain = retain
        self.do_escape = do_escape
        self.block_mode_processor = block_mode_processor

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
INDEXINFO = "indexinfo.toml"
ZWCFILEEXT = ".zwc"

# ################ GLOBALS ################
indir_base = INDIR
outdir_base = OUTDIR
templates = {}
FORMATTER = HtmlFormatter(linenos=False, cssclass="source")

def sp_image_linker(link):
    delim_index = link.rfind("/")
    return f"{link[:delim_index+1]}s_{link[delim_index+1:]}"

def block_processor_code(c, args, mode):
    lang = ""
    pre = "<div class=\"source\"><pre>" + c + "</pre></div>"
    try:
        lang = args[0]
        if lang == 'none':
            return pre
        lexer = get_lexer_by_name(lang, stripal=True)
        return highlight(c, lexer, FORMATTER)
    except IndexError:
        print(f"[WARN] Missing argument for mode '{mode}'")
        return pre
    except ClassNotFound:
        print(f"[WARN] Unknown language '{lang}' use 'none' for no highlighting")
        return pre


# NOTE: there are a few places in the index generation which hardcodes these
# tokens. If these are changed, be sure to change them in the index.zec generation!
SYNTXLUT = { # Filetype number, delimiter, delimiters per line, mode type, needs newline after template, modified parameter function
    "```"  : SP(500, "",  0, "code", False, None),   # CODE BLOCK TOGGLE
    "#"    : SP(501, "",  0, "none", True,  None),   # HEADING 1
    "##"   : SP(502, "",  0, "none", True,  None),   # HEADING 2
    "###"  : SP(503, "",  0, "none", True,  None),   # HEADING 3
    "=>"   : SP(504, " ", 1, "none", True,  None),   # HYPERLINK
    "=>>"  : SP(512, " ", 1, "none", True,  None),   # HYPERLINK - OFFSITE
    "*"    : SP(505, "",  0, "list", False, None),   # LIST ELEMENT
    ">"    : SP(506, "",  0, "none", False, None),   # BLOCKQUOTE
    "!"    : SP(507, " ", 1, "none", True,  None),   # IMAGE
    "!!"   : SP(508, " ", 1, "none", True,  sp_image_linker),     # IMAGE (with scaled link - full size is linked)
    "<@>"  : SP(509, "",  0, "html", False, None),   # HTML BLOCK TOGGLE
    "$"    : SP(510, "",  0, "none", False, None),   # CENTERED TEXT
    "!a"   : SP(511, " ", 2, "none", True,  None)    # AUDIO PLAYER
}
MODES = { #       BEGIN      END         STRIP  RETAIN ESCAPE block_mode_processor
    "none" : MODE("",        "",         True,  False, True,  None),
    "code" : MODE("",        "",         False, True,  False, block_processor_code),
    "html" : MODE("",        "",         True,  True,  False, None),
    "list" : MODE("<ul>",    "</ul>",    True,  False, True,  None)
}


# https://security.stackexchange.com/questions/66252/encodeuricomponent-in-a-unquoted-html-attribute
# Enocdes string to use HTML instead of raw characters
# Param: string: the string to be HTML encoded (using the HTML entities)
def encodehtml(string):
        return (string
                .replace("&", "&amp;")
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

    # Start content container
    contents = '\n<div id="content" class="container">'

    lines = zwc_file.readlines()
    ii = 0
    block = ""
    while ii < len(lines):
        line = lines[ii]
        ii += 1
        linestrip = line.strip()
        linestrip = linestrip.replace("\n", "") # This keeps leading whitespace!
        marker = ""
        if len(linestrip) > 0:
            fields = linestrip.split(maxsplit=1)
            marker = fields[0]
        marked = False

        # Check if this line starts with a marker
        sp = None
        try:
            sp = SYNTXLUT[marker]
            marked = True
        except KeyError:
            pass

        # Line contains a marker, set up mode if it changes the mode state
        if marked and (not MODES[mode].retain or mode == sp.mode):
            if sp.mode != "none":
                # If the mode is the same
                if sp.mode == mode:
                    # and it's set to be "sticky" with the retain
                    # flag, then disable the mode since we're
                    # already in it
                    if MODES[sp.mode].retain:
                        contents += MODES[mode].end
                        
                        # For modes that need to be processed as a single block, 
                        # do the processing here:
                        if MODES[mode].block_mode_processor != None:
                            contents += MODES[mode].block_mode_processor(block, mode_args, mode)
                        
                        mode_args = []
                        block = ""
                        mode = "none"
                # Different mode => end the current one and set
                # up the new one
                else:
                    contents += MODES[mode].end
                    mode = sp.mode
                    contents += MODES[mode].begin

            # Handle whitespace strip if necessary
            if MODES[mode].stripws:
                line = linestrip
            line = line[len(marker):]

            # Parse corresponding template and insert its contents
            try:
                contents += readtemplate(templates[sp.filenum], line.split(maxsplit=sp.dpl), sp.template_arg_modifier)
            except KeyError:
                print(f"[WARN] Encountered template id {sp.filenum} with no associated template file")

            # Some templates need a trailing newline for formatting purposes
            if sp.neednl:
                contents += "\n"

            # Set up arguments for block modes
            if MODES[mode].block_mode_processor != None:
                mode_args = line.split()

        # Line does not contain a marker
        else:
            # If the mode does not need to be retained
            # between lines, reset the mode
            if not MODES[mode].retain:
                contents += MODES[mode].end
                mode = "none"

            # Handle modes which require whitespace strip
            l2e = line
            if MODES[mode].stripws and linestrip != "":
                l2e = linestrip + "\n"

            # Only escape HTML characters if in a mode that requires escape sequences
            if MODES[mode].do_escape:
                l2e = encodehtml(l2e)
            
            # Handle blocks
            if MODES[mode].block_mode_processor == None:
                contents += l2e
            else:
                block += l2e


    if mode != "none":
        contents += MODES[mode].end
        
    # Close content container
    contents += "</div>\n"

    return contents


# Generates the HTML for the entire page (except that determined by the .zwc file)
def generatepage(file, templates):
    print(f"[INFO] Reading {file}")

    page_string = ""

    page_title = file.replace(indir_base, "", 1)

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

    zwc.close()

    return page_string, page_title


def generateallpages(in_files, indir, outdir):
    index_list = []
    total_pages = 0

    for filename in in_files:
        filebase, fileext = os.path.splitext(filename)
        file = os.path.join(indir, filebase + fileext)
        # If file is a regular file (not a folder), generate a page with it
        if os.path.isfile(file) and fileext == ZWCFILEEXT:
            file_contents, file_title = generatepage(file, templates)
            index_list.append(ZWCFile(filebase, fileext, file_title))
            file_to_write = os.path.join(outdir, filebase + ".html")
            try:
                with open(file_to_write, "w") as genfile:
                    genfile.write(file_contents)
                total_pages += 1
            except:
                print("[ERROR] Unable to write to " + file_to_write)
                exit(-1)
        elif os.path.isdir(file):
            sub_outdir = file.replace(indir_base, outdir_base, 1)
            index_title, pages_count = process_dir_recursive(file, sub_outdir)
            total_pages += pages_count
            index_list.append(ZWCFile(os.path.join(filebase, "index"), "", index_title))

    return index_list, total_pages


def process_dir_recursive(indir, outdir, is_root_dir=False):
    
    # Remove the index file
    index_file = os.path.join(indir, INDEXZWC)
    try:
        os.remove(index_file)
    except:
        print(f"[INFO] No previous {index_file} file detected")
    
    try:
        os.mkdir(outdir)
        print(f"[INFO] Created output directory '{outdir}'")
    except FileExistsError:
        print(f"[INFO] Output directory exists ({outdir})")
        

    index_list, total_pages = generateallpages(os.listdir(indir), indir, outdir)

    index_list.sort()

    indexinfo = {}
    index_title = ""
    index_desc = ""
    index_ignore = []
    try:
        with open(os.path.join(indir, INDEXINFO), "rb") as indexinfo_file:
            indexinfo = tomllib.load(indexinfo_file)
            index_title = indexinfo['index']['title'].strip()
            index_desc = indexinfo['index']['desc'].strip()
            index_ignore = indexinfo['hidden']['pages']
    except FileNotFoundError:
        print("[WARN] Unable to open index info file")
    except tomllib.TOMLDecodeError as e:
        print(f"[ERROR] Errors encountered while parsing {INDEXINFO}")
        print(e)
        exit(-1)

    if not is_root_dir and len(index_title) == 0:
        print("[ERROR] Sub directory index missing title!")
        exit(-1)
        
    try:
        with open(index_file, "w") as indexfile:
            # If this is a subdirectory, put links to the parent directories
            if not is_root_dir:
                pd = indir.replace(indir_base, "", 1)
                sp = os.path.split(pd)
                if sp[0] != '' and sp[1] != '':
                    indexfile.write(f"=> ../index.html Up to {sp[0]}")
                    indexfile.write("\n\n")

            # If an index title is specified, use that instead
            if (len(index_title) == 0):
                indexfile.write("# Index\n")
            else:
                indexfile.write(f"# {index_title}\n")

            # If an index description is specified, insert it
            if (len(index_desc) > 0):
                indexfile.write(f"{index_desc}\n\n")

            # Now list all the files for this index listing level
            for element in index_list:
                if element.filebase not in index_ignore:
                    indexfile.write(f"=> {element.filebase}.html {element.title}\n")
    except Exception as e:
        print("[WARN] Unable to generate index file")
        print(e)

    index_list, pages = generateallpages([INDEXZWC], indir, outdir)
    total_pages += pages
    return index_title, total_pages


if __name__ == "__main__":

    argv = sys.argv[1:]
    
    templatedir = TEMPLATEDIR

    try:
        opts, args = getopt.getopt(argv, "i:o:t:", ["in-dir=", "out-dir=", "template-dir="])
    except getopt.GetoptError:
        print("[ERROR] Unknown option!")
        exit (-1)
    
    for opt, arg in opts:
        if opt in ['-i', "--in-dir"]:
            indir_base = arg
        elif opt in ['-o', "--out-dir"]:
            outdir_base = arg
        elif opt in ['-t', "--template-dir"]:
            templatedir = arg
        else:
            print("[SPCL] Somehow an unknown arg got past the arg parser")

    # Template loading
    template_listing = os.listdir(templatedir)
    template_listing.sort()
    for filename in template_listing:
        file = os.path.join(templatedir, filename)

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
                # Concatenate lines which do not start with a comment
                template_str = ""
                for ll in f.readlines():
                    if not ll.startswith('#'):
                        template_str += ll
                
                # Add template string to available templates
                templates.update( {
                    filenum : Template(filename, filenum, template_str)
                } )

    total_pages = process_dir_recursive(indir_base, outdir_base, is_root_dir=True)
                
    print(f"[INFO] DONE! Total pages {total_pages}")
