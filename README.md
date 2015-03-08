sudo apt-get update
sudo apt-get install python-pip python-dev python-numpy python-scipy python-pyaudio git-core
git clone http://github.com/krillr/pfsk
cd pfsk
sudo pip install -r requirements.txt
python schmetterling.py
