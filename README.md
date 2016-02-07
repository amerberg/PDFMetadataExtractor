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
Configuration is via a YAML settings file. A sample settings file is provided in `settings.sample.yml`.

Fields to be extracted are specified in `fields`. 
Each key specifies a single metadata field.
A field is represented by a hash (dictionary) containing the following keys:

    -   `module` - The name of the module in which the field type class is defined.
    -   `class` - The name of the class for this field type. This class should extend `field.Field`
    -   `parameters` (optional) - A hash of parameters to be passed to the class's constructor. 
    -   `labels` - A list of labels that might be used to label this field.
    -   `candidate_finders` - A hash of candidate finder definitions, explained in more detail below.
    -   `features` - A hash of feature definitions, explained in more detail below.
    
A candidate finder is defined by a hash with the following keys:

    -   `module` - The name of the module in which the candidate finder class is defined.
    -   `class` - The name of the class for this candidate finder. This class should extend `candidate.CandidateFinder`
    -   `parameters` (optional) - A hash of parameters to be passed to the class's constructor. 
  
A feature is defined by a hash with the following keys:

    -   `module` - The name of the module in which the feature is defined.
    -   `class` - The name of the class for this feature. This class should extend `feature.Feature`
    -   `parameters` (optional) - A hash of parameters to be passed to the class's constructor.
     
Some basic field types are included in `py/fields.py`.
Some basic candidate finders are defined in `py/label_candidate_finder.py` and `py/box_phrase_candidate_finder.py`
Some basic features can be found in `py/features.py`.

The settings file should also specify the following keys:

    -   `substitutions` - a hash whose keys are single characters and whose items are lists of strings likely to be substituted for those keys by the OCR software in use.
    -   `files` - a hash of files. 
            So far, the only key used is `labels`, which should be a JSON file containing correct metadata values for training data.
    -   `directories` a hash of directories. The following keys might be used `pickle`, `model_definition`, `csv`, `pdf`.
            The PDFs to be read should be in the `pdf` directory.
            To use `markup.py`, the `marked_pdf` directory should also be supplied.
            All directories supplied should already exist, as they will not be created automatically.
    -   `db` - A hash of settings for a SQLAlchemy database engine.
            The following keys should be defined: `backend`, `username`, `password`, `server`, `port`, and (database) `name`.
            Optionally, `charset` may also be supplied.
            The only backend that has been tested so far is `pymysql` but others might work.
            More information on these parameters is available in [SQLAlchemy documentation](http://docs.sqlalchemy.org/en/latest/core/engines.html).
    -   `extra_labels` - A list of label texts to be ignored for all fields. 


More details will be provided very soon.