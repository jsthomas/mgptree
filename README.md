# mgptree

A CLI tool for making "family trees" from the Mathematics Genealogy Project.

## What is this?

`mgptree` allows you to automatically collect data from the
Mathematics Genealogy project and convert that data to format `dot`
can consume to produce a directed graph of advisor-advisee
relationships (similar to a family tree). You can see an extended
example
[here](https://jsthomas.github.io/math-genealogy-visualizer.html).

## Install

You will need to install [`graphviz`](http://www.graphviz.org/), and
possibly `virtualenv` as well. Then:

    $ virtualenv venv
    $ venv/bin/activate
    (venv) $ pip install requirements.txt
    (venv) $ python mgptree.py -h

should show you the command line syntax for the tool.

## Usage

This tool has two modes, "scraping" and "plotting". In scraping mode,
you specify an input list of names, and a number of "generations" to
search backward starting from those names (10-20 is a reasonable
depth). A typical input file looks like:

```
Gauß, Carl, Friedrich
Fourier, Jean-Baptiste, Joseph
```

(In terms of formatting, the program expects one name per line,
ordered _last_, _first_, _middle_, where the middle name is optional.)


This produces a "database" (pickled python object file) of records
about different mathematicians. In plotting mode, the tool takes this
database as input and a number of generations, and produces a dotfile
for that many generations back from the leaves. Generally, scraping is
more time consuming than plotting. Specifying the number of
generations during plotting lets you see more or less of your dataset,
without having to do an expensive re-scrape.
