import unittest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import ConfigParser as SafeConfigParser

import yaml

from confirm import generator, utils


def config_from_config_string(config_string):
    config_parser = SafeConfigParser()
    config_parser.readfp(StringIO(config_string))
    return utils.config_parser_to_dict(config_parser)


class AppendValuesTestCase(unittest.TestCase):

    def test_append(self):
        config_string = "[section]\noption1=value1\noption2=value2"
        schema_string = """
        "section":
            "option1":
                "required": true
            "option2":
                "required": true
            "option3":
                "required": true
        """.strip()

        schema = yaml.load(StringIO(schema_string))
        config = config_from_config_string(config_string)

        migrated_config = generator.append_existing_values(schema, config)

        self.assertIn('section', migrated_config)
        self.assertIn('option3', migrated_config['section'])
        self.assertIn('required', migrated_config['section']['option3'])
        self.assertNotIn('value', migrated_config['section']['option3'])

        self.assertIn('value', migrated_config['section']['option1'])
        self.assertIn('value', migrated_config['section']['option2'])


class GenerateSchemaTestCase(unittest.TestCase):

    def test_init(self):
        config_string = "[section]\noption1=value1\noption2=value2"
        schema_string = generator.generate_schema_file(config_string)

        schema = yaml.load(StringIO(schema_string))
        self.assertIn('section', schema)
        self.assertIn('option1', schema['section'])
        self.assertIn('description', schema['section']['option1']['description'])
        self.assertEqual('No description provided.', schema['section']['option1']['description'])


class GenerateConfigParserTestCase(unittest.TestCase):

    def test_empty_config(self):
        config_parser = generator.generate_config_parser({})
        self.assertFalse(len(config_parser.sections()))

    def test_required(self):
        config = {"section":
                     {"option":
                         {"required": True}
                     }
                 }
        config_parser = generator.generate_config_parser(config)
        options = config_parser.options('section')
        self.assertIn('option', options)
        self.assertIn('# required', options)

        value = config_parser.get('section', 'option')
        self.assertEqual(value, 'TO FILL')

    def test_required_default(self):
        config = {"section":
                     {"option":
                         {"required": True, "default": 12}
                     }
                 }
        config_parser = generator.generate_config_parser(config)
        value = config_parser.get('section', 'option')
        self.assertEqual(value, '12')

    def test_required_default(self):
        config = {"section":
                     {"option":
                         {"required": True, "default": 12, "value": 25}
                     }
                 }
        config_parser = generator.generate_config_parser(config)
        options = config_parser.options('section')
        self.assertIn('option', options)
        self.assertIn('# required', options)

        value = config_parser.get('section', 'option')
        self.assertEqual(value, '25', "We should use the existing value instead of the default!")

    def test_options(self):
        config = {"section":
                     {"optiona":
                         {"required": True, "default": 'DA',  "value": 'VA'},
                      "optionb":
                         {"required": True, "default": 'DB'}
                     }
                 }

        config_parser = generator.generate_config_parser(config)
        options = config_parser.options('section')

        self.assertIn('optiona', options)
        value = config_parser.get('section', 'optiona')
        self.assertEqual(value, 'VA')

        self.assertIn('optionb', options)
        value = config_parser.get('section', 'optionb')
        self.assertEqual(value, 'DB')

    def test_generate_include_all(self):
        config = {"section":
                     {"optiona":
                         {"required": True, "default": 'DA',  "value": 'VA'},
                      "optionb":
                         {"default": 'DB'}
                     }
                 }

        config_parser = generator.generate_config_parser(config)
        options = config_parser.options('section')
        self.assertNotIn('optionb', options)

        config_parser = generator.generate_config_parser(config, include_all=True)
        options = config_parser.options('section')
        self.assertIn('optionb', options)

        value = config_parser.get('section', 'optionb')
        self.assertEqual(value, 'DB')


class GenerateDocumentationTestCase(unittest.TestCase):

    def _call_generate_documentation(self, schema_string):
        schema = yaml.load(StringIO(schema_string))
        return generator.generate_documentation(schema)

    def test_basic_case(self):
        schema = """
        "section":
            "option":
                "required": true
                "description": "This is a description."
        """.strip()

        documentation = self._call_generate_documentation(schema).split('\n')

        self.assertIn("Configuration documentation", documentation)
        self.assertIn("section", documentation)
        self.assertIn("option", documentation)
        self.assertIn("This is a description.", documentation)

    def test_option_with_type(self):
        schema = """
        "section":
            "option":
                "required": true
                "type": "bool"
        """.strip()

        documentation = self._call_generate_documentation(schema).split('\n')

        self.assertIn("*Type : bool.*", documentation)

    def test_deprecated(self):
        schema = """
        "section":
            "option":
                "required": true
                "deprecated": true
                "type": "bool"
        """.strip()

        documentation = self._call_generate_documentation(schema).split('\n')

        self.assertIn('** This option is deprecated! **', documentation)
        self.assertIn('** This option is required! **', documentation)

    def test_default(self):
        schema = """
        "section":
            "option":
                "default": "1"
        """.strip()

        documentation = self._call_generate_documentation(schema).split('\n')

        self.assertIn("The default value is 1.", documentation)
