"""Base class for a model"""



class CompletionModel(object):
    """Base class for a language model"""
    _registry = {}    # the registry of all created models

    config = {}
    max_tokens = 2000
    default_options = {}
    name = None

    def __init_subclass__(cls, name=None, max_tokens=None, config=None, default_options=None):
        """Register a new model through subclass hook"""
        cls._initialized = False
        if name:
            cls._registry[name] = cls
            cls.name = name
        if max_tokens:
            cls.max_tokens = max_tokens
        cls.config = dict(cls.config or {})
        if config:
            cls.config.update(config)
        if default_options:
            cls.default_options = default_options
        cls._model_data = None

    def __init__(self, config=None, model_options=None):
        """Initialize a model, optionally override default config"""
        if config:
            self.config = self.config.copy()
            self.config.update(config)
        self.model_options = self.default_options.copy()
        if model_options:
            self.model_options.update(model_options)

    @classmethod
    def get(cls, name, config=None):
        """Retrieve a model class by name"""
        if isinstance(name, cls):
            return name
        if name not in cls._registry:
            raise KeyError(f'Model {name} not found in registry. Available: {cls._registry.keys()}')
        ModelClass = cls._registry[name]
        model = ModelClass(config=config)
        if model._model_data is None:
            ModelClass._model_data = model.initialize()
        return model
    
    def initialize(self):
        """Initialize a model if it has been retrieved. 
        This is to make initializations lazy and avoid loading all models upfront
        """
        return {}
        
    def get_completion(
        self,
        messages,               # a list of exchanges.  or a string if there is only one question.
        system_prompt='',       # context to be injected into the prompt before the conversation
        text_only=False,        # returns text directly instead of the normal response object with choices
        lead='',                # Force agent to start its answer with this string.  Not all models will honor this
        callback=None,          # if given, progressive response will call this routine
        **model_options
    ):
        """Get the next response from the language model"""
        raise NotImplementedError(f'get_completion() is not implemented for {type(self)}')
    
    def token_count(self, text):
        """Return the number of tokens in a text segment"""
        raise NotImplementedError(f'token_count() is not implemented for {type(self)}')
    
    @property
    def model_data(self):
        return self._model_data
    
    