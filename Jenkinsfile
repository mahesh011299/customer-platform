pipeline {
    agent any

    parameters {
        choice(name: 'ENVIRONMENT', choices: ['DEV', 'UAT', 'PRODUCTION'], description: 'Deployment Environment')
        choice(name: 'ACTION', choices: ['DEPLOY', 'ROLLBACK'], description: 'Deployment Action')
        string(name: 'VERSION', defaultValue: '5.0', description: 'Application Version')
        choice(name: 'RUN_TESTS', choices: ['YES', 'NO'], description: 'Run test suite')
        choice(name: 'CONFIRM_PROD', choices: ['NO', 'YES'], description: 'Required YES for PRODUCTION')
    }

    environment {
        PATH = "C:\\Program Files\\Docker\\Docker\\resources\\bin;C:\\Users\\HP\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin;${env.PATH}"
        DB_PWD = credentials('db-password')
    }

    stages {
        stage('Resolve Configuration') {
            steps {
                script {
                    if (params.ENVIRONMENT == 'PRODUCTION' && params.CONFIRM_PROD != 'YES') {
                        error("PRODUCTION deployment aborted: CONFIRM_PROD must be 'YES'.")
                    }

                    def configMap = [
                        'DEV': [
                            branch: 'develop',
                            app: 'customer-app-dev',
                            port: '8081',
                            net: 'customer-dev-net',
                            db: 'customer-db-dev',
                            vol: 'pgdata-dev'
                        ],
                        'UAT': [
                            branch: 'release',
                            app: 'customer-app-uat',
                            port: '8082',
                            net: 'customer-uat-net',
                            db: 'customer-db-uat',
                            vol: 'pgdata-uat'
                        ],
                        'PRODUCTION': [
                            branch: 'main',
                            app: 'customer-app-prod',
                            port: '8083',
                            net: 'customer-prod-net',
                            db: 'customer-db-prod',
                            vol: 'pgdata-prod'
                        ]
                    ]

                    def activeConfig = configMap[params.ENVIRONMENT]
                    env.TARGET_BRANCH = activeConfig.branch
                    env.APP_NAME      = activeConfig.app
                    env.HOST_PORT     = activeConfig.port
                    env.NETWORK       = activeConfig.net
                    env.DB_NAME       = activeConfig.db
                    env.VOLUME_NAME   = activeConfig.vol

                    echo """
                    ================ DEPLOYMENT RESOLUTION ================
                    ENVIRONMENT     : ${params.ENVIRONMENT}
                    GIT BRANCH      : ${env.TARGET_BRANCH}
                    CONTAINER APP   : ${env.APP_NAME}
                    HOST PORT       : ${env.HOST_PORT}
                    DOCKER NETWORK  : ${env.NETWORK}
                    DB CONTAINER    : ${env.DB_NAME}
                    PERSISTENT VOL  : ${env.VOLUME_NAME}
                    DEPLOY VERSION  : ${params.VERSION}
                    ======================================================
                    """
                }
            }
        }

        stage('Network and Volume Setup') {
            steps {
                bat """
                    docker network create ${env.NETWORK} 2>NUL || exit /b 0
                    docker volume create ${env.VOLUME_NAME} 2>NUL || exit /b 0
                """
            }
        }

        stage('Deploy Database') {
            steps {
                script {
                    bat """
                        docker inspect ${env.DB_NAME} >nul 2>&1 || ^
                        docker run -d --name ${env.DB_NAME} ^
                            --network ${env.NETWORK} ^
                            -v ${env.VOLUME_NAME}:/var/lib/postgresql/data ^
                            -e POSTGRES_DB=customer_db ^
                            -e POSTGRES_USER=postgres ^
                            -e POSTGRES_PASSWORD=${env.DB_PWD} ^
                            postgres:16-alpine
                    """
                    echo "Waiting 8 seconds for database service initialization..."
                    sleep time: 8, unit: 'SECONDS'
                }
            }
        }

        stage('Docker Build') {
            steps {
                bat "docker build -t customer-app:${params.VERSION} ."
            }
        }

        stage('Deploy Application & Validate') {
            steps {
                script {
                    try {
                        echo "Deploying ${env.APP_NAME} on port ${env.HOST_PORT}..."
                        bat "docker rm -f ${env.APP_NAME} 2>NUL || exit /b 0"

                        bat """
                            docker run -d --name ${env.APP_NAME} ^
                                --network ${env.NETWORK} ^
                                -p ${env.HOST_PORT}:8080 ^
                                -e ENVIRONMENT=${params.ENVIRONMENT} ^
                                -e APP_VERSION=${params.VERSION} ^
                                -e DB_HOST=${env.DB_NAME} ^
                                -e DB_NAME=customer_db ^
                                -e DB_USER=postgres ^
                                -e DB_PASSWORD=${env.DB_PWD} ^
                                customer-app:${params.VERSION}
                        """

                        echo "Waiting 10 seconds for container startup..."
                        sleep time: 10, unit: 'SECONDS'

                        echo "--- Validation 1: Verify Network Attachment ---"
                        bat "docker network inspect ${env.NETWORK}"

                        echo "--- Validation 2: Application Health & DB Reachability ---"
                        bat "curl --fail http://localhost:${env.HOST_PORT}/health"

                        echo "--- Validation 3: Customer Search Feature Test ---"
                        bat "curl --fail http://localhost:${env.HOST_PORT}/customers?query=retail"

                    } catch (Exception e) {
                        echo "=========================================================="
                        echo "VALIDATION FAILED! TRIGGERING AUTOMATIC ROLLBACK TO 5.0"
                        echo "=========================================================="

                        bat "docker rm -f ${env.APP_NAME} 2>NUL || exit /b 0"
                        bat """
                            docker run -d --name ${env.APP_NAME} ^
                                --network ${env.NETWORK} ^
                                -p ${env.HOST_PORT}:8080 ^
                                -e ENVIRONMENT=${params.ENVIRONMENT} ^
                                -e APP_VERSION=5.0 ^
                                -e DB_HOST=${env.DB_NAME} ^
                                -e DB_NAME=customer_db ^
                                -e DB_USER=postgres ^
                                -e DB_PASSWORD=${env.DB_PWD} ^
                                customer-app:5.0
                        """
                        sleep time: 8, unit: 'SECONDS'
                        bat "curl --fail http://localhost:${env.HOST_PORT}/health"
                        echo "Rollback restored customer-app:5.0 on port ${env.HOST_PORT}."

                        currentBuild.result = 'FAILURE'
                        error("Deployment validation failed; automated rollback to 5.0 was executed.")
                    }
                }
            }
        }
    }
}