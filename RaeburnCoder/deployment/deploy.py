# Automated Deployment to App Store & Play Store
import os

def deploy_app():
    os.system("fastlane deploy")
    return "App Deployed Successfully!"
