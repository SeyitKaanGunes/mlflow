pipeline {
    agent any

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

        stage('Python Dependencies') {
            steps {
                bat '''
                  python -m venv .venv
                  call .venv\\Scripts\\activate
                  python -m pip install --upgrade pip
                  pip install -r requirements.txt
                '''
            }
        }

        stage('Train Model') {
            steps {
                bat '''
                  call .venv\\Scripts\\activate
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
            bat 'if exist .venv rmdir /S /Q .venv'
        }
    }
}
