# About
Workflow for the Omdena pipeline.

# Getting Started

1. **Configure Server**
   - Python 3.12
   - Ubuntu 24.01
   - GDAL 3.9.3
   - venv
   ```bash
   sudo apt update
   sudo apt install python3-venv
   ```

2. **Setup Github ssh**
```bash
ssh-keygen
```
Copy the ssh key to the github.

3. **Clone the repo**
```bash
git clone git@github.com:shashigharti/omdena-workflow.git
```

4. **Install pygmstar**
   - Set it to executable
      ```bash
      chmod +x scripts/install.sh
      ```
   - Run the script:
     ```bash
     ./scripts/install.sh
     ```
     * Note make sure that GMTSAR library is installed correctly
   - Set the environment variables, if not set:
     ```bash
     export GMTSAR_PATH=/usr/local/GMTSAR
     export PATH=$GMTSAR_PATH/bin:$PATH
     ```
3. **Create a new virtual environment**
   ```bash
   python3 -m venv envs/guardian
   . envs/guardian
   ```
4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
5. **Create the .env file and set the environment variables**
   ```bash
   sudo vi .env
   ```
   Add following variables:

   USER_USERNAME=admin
   USER_PASSWORD=admin123
   WORKDIR=/home/shashi-gharti/python/omdena/GuardianSpaceGeo/data/raw_kahr
   DATADIR=/home/shashi-gharti/python/omdena/GuardianSpaceGeo/data/data_kahr
   OUTPUT=/home/shashi-gharti/python/omdena/GuardianSpaceGeo/data/output
   ASF_USERNAME=GoogleColab2023
   ASF_PASSWORD=GoogleColab_2023
   AWS_ACCESS_KEY=AKIARWIL
   AWS_SECRET_KEY=lYJYWg00kU
   SH_CLIENTID=AKIARWILO5
   SH_CLIENT_SECRET=8XufSzKnyre6y4S6
   USE_SAMPLE_BURSTS=true
   LOG_FILENAME=/home/shashi-gharti/python/omdena/GuardianSpaceGeo/server/app.log
   SQLALCHEMY_DATABASE_URL=sqlite:////home/ubuntu/GuardianSpaceGeo/guardian.db


5. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

6. **Run the Application**
```
uvicorn main:app --reload
```
The application should be running at http://localhost:8000
