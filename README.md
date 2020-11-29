# mgptree

A CLI tool for making "family trees" from the [Mathematics Genealogy Project](https://genealogy.math.ndsu.nodak.edu/).

## What is this?

The Mathematics Genealogy Project records advisor-advisee relationships between mathematicians, 
going back hundreds of years. `mgptree` allows you to plot these relationships to produce a directed graph,
similar to a family tree. You can see an extended example [here](https://jsthomas.github.io/math-genealogy-visualizer.html).

## Install

This tool uses Python 3.7.3. You will need to install [`graphviz`](http://www.graphviz.org/), and
possibly `virtualenv` as well (depending on where you prefer to
install your python libraries). Here is how I set up:

    $ virtualenv venv
    $ venv/bin/activate
    (venv) $ pip install -r requirements.txt
    (venv) $ python mgptree.py -h

This should show you the command line syntax for the tool.

## Usage

This tool has two modes, "scraping" and "plotting". In scraping mode,
you specify an input list of names and a number of "generations" to
search backward starting from those names (10-20 is a reasonable
depth). A typical input file looks like:

```
Gauß, Carl, Friedrich
Fourier, Jean-Baptiste, Joseph
```

(In terms of formatting, the program expects one name per line,
ordered _last_, _first_, _middle_, where the middle name is optional.)

Scraping produces a pickled python object file of records
about different mathematicians. In plotting mode, the tool takes this
file as input and a number of generations, and produces a dotfile
for that many generations back from the roots (your original names). Scraping is typically
more time consuming than plotting. Specifying the number of
generations during plotting lets you see more or less of your dataset,
without having to do an expensive re-scrape.

## Example Session

Let's build a tree for Alan Turing.

```
echo "Turing, Alan, Mathison" > names.txt
python mgptree.py --scrape --generations 10 --input names.txt --output turing.mgp
python mgptree.py --plot --generations 10 --input turing.mgp --output turing.dot
dot -Tpng turing.dot -o turing.png
```

If all went well, `turing.png` should look like this:

![A picture of Turing's advisor tree.](https://github.com/jsthomas/mgptree/blob/master/turing.png?raw=True)