# lane-mark2tuSimple

The doc of TuSimple format: https://github.com/TuSimple/tusimple-benchmark/tree/master/doc/lane_detection#directory-structure

The page of the above link also shows the usage of evalation tool. You can learn the metric caculation by learning it.


## Usage 

You can run this script easily by

`python xml2tuSimple.py -i <folder_name>`

or

`python xml2tuSimple.py -i <file_path>`

## Appendix

This section is the notes when I tackled bugs.

### XML files

XML file can be parsed by XML.SAX, but it's a little 
troublesom: https://www.runoob.com/python/python-xml.html

I find it can be parsed by lxml.etree, too. So I use the lxml package to process it. 

Though the function `ml2dict_recursively_by_node` use the XML package of pure python, I cannot find the attribute 
of the node.

Then, I find the attribute of a node can be find with the lxml package. So I don't have the enough time to study the official XML package and will use the lxml package to tackle this problem. 
For getting the "id" of the "filename" node in our example xml file.

    from lxml import etree 
    
    file = "factory_in_1_1.xml"
    f = open(file)
    t = f.read()
    f.close()
    
    t_bytes = t.encode("utf-8") # this is important for the api of etree.XML
    xml_obj = etree.XML(t_bytes)
    print("the tag of root node" ,xml_obj.tag)
    
    target_tagname = "filename"
    target_key = "id"
    for child in xml_obj:
        if child.tag == target_tagname:
            target_value = child.attrib[target_key] # child.atrrib's type is <class 'lxml.etree._Attrib'> , but you can exploit it like the dict.
    
    print("your target value of {} is {}".format(
        target_key, target_value
    ))