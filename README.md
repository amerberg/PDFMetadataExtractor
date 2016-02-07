#PDFMetaDataExtractor

This is a Python tool for extracting metadata from PDFs.
It assumes that the PDFs have embedded OCR text, but it allows for the possibility of noisy OCR text.

##How it works
`PDFMetaDataExtractor` takes a two-phase approach to identifying metadata fields in documents.

The first phase is the generation of _candidates_, typically by means of a pattern-matching approach.
The idea here is to use some kind of primitive human intuitions to identify a few bits of text that probably contain the data of interest.

Once candidates have been identified, a machine learning approach can be taken to identify the correct ones, provided that training data is available.
The basic approach here is to score all candidates in training documents by their similarity to the real value and then train a regressor to use text features to predict match scores.
When a new document comes in, candidates are identified, scores are predicted using the trained regression model, and the highest (predicted) scoring candidate is chosen.

##Configuration
Configuration is via a YAML settings file. 
More details will be provided very soon.