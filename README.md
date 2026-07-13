# Plonetheme Pagelet Base

A Plone theme base for themes based on pagelets

## Features

- Compatible with Plone 6.2+

## Installation

Add `plonetheme.pageletbase` to your project's dependencies:

```python
# In your pyproject.toml
dependencies = [
    "plonetheme.pageletbase",
    # ...
]
```

Then activate the addon in your Plone site's control panel or via GenericSetup.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/collective/plonetheme.pageletbase.git
cd plonetheme.pageletbase

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[test]"
```

### Running Tests

```bash
pytest
```

### Running Tests with Coverage

```bash
pytest --cov=plonetheme.pageletbase --cov-report=html
```

## License

GPL-2.0-or-later

## Author

Maik Derstappen <md@derico.de>
