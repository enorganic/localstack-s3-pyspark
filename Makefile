# python 3.6 is used, for the time being, in order to ensure compatibility
install:
	{ python3.7 -m venv venv || py -3.7 -m venv venv ; } && \
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	{ pip3 install --upgrade pip wheel || echo ""; } && \
	pip3 install\
	 -r requirements.txt\
	 -e . && \
	localstack-s3-pyspark configure-defaults && \
	{ mypy --install-types --non-interactive || echo '' ; } && \
	echo "Success!"

ci-install:
	{ python3 -m venv venv || py -3 -m venv venv ; } && \
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	{ pip3 install --upgrade pip wheel || echo ""; } && \
	pip3 install\
	 -r requirements.txt\
	 -e . && \
	echo "Success!"

# Install dependencies locally where available
editable:
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	daves-dev-tools install-editable --upgrade-strategy eager && \
	make requirements && \
	echo "Success!"

# Cleanup unused packages, and Git-ignored files (such as build files)
clean:
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	daves-dev-tools uninstall-all\
	 -e .\
     -e pyproject.toml\
     -e tox.ini\
     -e requirements.txt && \
	daves-dev-tools clean && \
	echo "Success!"

# Distribute to PYPI
distribute:
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	daves-dev-tools distribute --skip-existing && \
	echo "Success!"

# Upgrade
upgrade:
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	daves-dev-tools requirements freeze\
	 -nv '*'\
	 '.[all]' pyproject.toml tox.ini daves-dev-tools\
	 > .requirements.txt && \
	pip3 install --upgrade --upgrade-strategy eager\
	 -r .requirements.txt '.[all]' && \
	rm .requirements.txt && \
	make requirements

# Update requirement version #'s to match the current environment
requirements:
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	daves-dev-tools requirements update\
	 -i pyspark\
	 -aen all\
	 setup.cfg pyproject.toml tox.ini && \
	daves-dev-tools requirements freeze\
	 -e pip\
	 -e wheel\
	 -nv setuptools -nv filelock -nv platformdirs\
	 . pyproject.toml tox.ini daves-dev-tools\
	 > requirements.txt && \
	echo "Success!"

# Run all tests
test:
	{ . venv/bin/activate || venv/Scripts/activate.bat ; } && \
	pip3 install tox && \
	tox -r
