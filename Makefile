install:
	(python3.6 -m venv venv || python3 -m venv venv) && \
	venv/bin/pip3 install --upgrade pip && \
	venv/bin/pip3 install --upgrade twine -c requirements.txt && \
	venv/bin/pip3 install -r requirements.txt -e . && \
	mypy --install-types --non-interactive

clean:
	venv/bin/daves-dev-tools uninstall-all\
	 -e .\
     -e pyproject.toml\
     -e tox.ini\
     -e requirements.txt && \
	venv/bin/daves-dev-tools clean

requirements:
	venv/bin/daves-dev-tools requirements update\
	 -i pyspark\
	 setup.cfg\
	 pyproject.toml\
	 tox.ini && \
	venv/bin/daves-dev-tools requirements freeze\
	 -nv docker-compose -nv docker -nv dockerpty\
	 . pyproject.toml tox.ini\
	 >> .requirements.txt && \
	rm requirements.txt && \
	mv .requirements.txt requirements.txt

distribute:
	venv/bin/daves-dev-tools distribute --skip-existing --verbose

test:
	venv/bin/tox -r -p all

upgrade:
	venv/bin/daves-dev-tools requirements freeze\
	 -nv '*' . pyproject.toml tox.ini\
	 >> .unversioned_requirements.txt && \
	venv/bin/pip3 install --upgrade --upgrade-strategy eager\
	 -r .unversioned_requirements.txt && \
	rm .unversioned_requirements.txt && \
	make requirements
