
# Zach's Web Compiler Spec

## Compiler File Structure

```
$ tree
.
├── compile.py
├── genpages
│   └── index.html [Auto Generated]
├── rawpages
│   ├── index.zwc [Auto Generated]
│   └── indexinfo.toml [User Created]
└── templates

```

## Templates

Each template HTML file begins with a number indicating the section of the to-be rendered page it represents.

```
* 000:     [M] HTML start
* 001-089: [O] header files (placed in "HEAD")
* 090:     [M] TITLE tag for page (placed in "HEAD")
* 091:     [R] STYLE tag for page (placed in "HEAD")
* 100-199: [N] included files (not implemented, placed in "HEAD")
* 200-299: [R] website "top/nav section" (placed in "BODY")
* 300-399: [U] unused
* 400-499: [U] unused
* 500-599: [M] formatting for special text (placed in "BODY")
* 600-699: [U] unused
* 700-799: [U] unused
* 800-899: [R] website "bottom/nav section" (placed in "BODY")
* 900-998: [U] unused
* 999:     [M] HTML end text

Key:
* [M] - Mandatory, must be present and fit standard description
* [R] - Recommended, not necessary to generate a page
* [O] - Optional, may be used as needed
* [U] - Currently unimplemented, saved for future expansion
* [N] - Not currently implemented and should not be used
```

For all type 090 and 5XX templates, the location where text is to be inserted should be marked by a line that starts with a "%". (The line should not have any preceding characters, including whitespace).

## Creating a Page

Write your text into a page using the following syntax then save your file with the .zwc file extension. Run the "compile.py" script in the ZWC root directory and all files in the "rawpages" directory will be compiled into static HTML documents. The compiled documents are placed in the "genpages" directory and can be served directly.

If you want you page to have a "<title>" then make sure that the .zwc file contains a line starting with a heading 1 start identifier: "#". If no heading 1 is found in the file, the "<title>" tag of the page should contain the filename of the .zwc file (note: while not a strict requirement, when the web compiler generates a "<title>" tag from the filename, the .zwc extension should be, preferably, excluded).

## Other Features

### indexinfo.toml

Every subdirectory of the "rawpages" directory (including the "rawpages" directory itself) should contain a file called "indexinfo.toml" This specifies information for the directory such as the header for the index page and an optional description. An example file is below:

```
# This information is displayed on the
# index page for this directory
[index]
title = "Home"
desc = "Welcome to my place on the web!"

# These zwc files are ignored and not
# added to the index listing
[hidden]
pages = [ "about" ]
```

### Disabling Index Listing of Specific Pages

To disable the auto listing of specific pages in the "index" file, add your hidden files' base names to the "pages" array under the [hidden] section in the "rawpages/indexinfo.toml" file

### Prevent Compilation of Specific Files

Not sure if this is a "feature," but if the file ending is something other than ".zwc" then the compiler will not compile the file. (Its associated generated html file will also be deleted if it previously existed.)

## My Compiler

If you would like to try out the web compiler for yourself, I have my python script (used to generate this website) available at:

=> https://github.com/ElectronicsTinkerer/wc-v2

