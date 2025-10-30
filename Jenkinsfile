pipeline {
    agent {
        docker {
            image 'python:3.10-slim'
            args '-u root:root'
        }
    }

    options {
        timestamps()
        skipDefaultCheckout(true)
    }

    environment {
        MLFLOW_TRACKING_URI = "file:${WORKSPACE}/mlruns"
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('System Packages') {
            steps {
                sh '''
                  set -e
                  apt-get update
                  apt-get install -y --no-install-recommends build-essential git libglib2.0-0 libgl1-mesa-glx
                  rm -rf /var/lib/apt/lists/*
                '''
            }
        }

        stage('Python Dependencies') {
            steps {
                sh '''
                  set -e
                  python -m venv .venv
                  . .venv/bin/activate
                  python -m pip install --upgrade pip
                  pip install -r requirements.txt
                '''
            }
        }

        stage('Train Model') {
            steps {
                sh '''
                  set -e
                  . .venv/bin/activate
                  python main.py --samples 200 --time-limit 60 --experiment-name JenkinsDemo
                '''
            }
        }
    }

    post {
        success {
            archiveArtifacts artifacts: 'artifacts/**/*', fingerprint: true, allowEmptyArchive: true
            archiveArtifacts artifacts: 'mlruns/**/*', fingerprint: true, allowEmptyArchive: true
        }
        always {
            sh 'rm -rf .venv'
        }
    }
}
