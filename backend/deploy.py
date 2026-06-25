import os
import zipfile
import subprocess

APP_FILES = ["server.py", "lambda_handler.py", "context.py", "resources.py"]


def build_docker_shell_command() -> str:
    app_copy_steps = " && ".join(
        f"( [ -f /var/task/{file} ] && cp /var/task/{file} /var/task/lambda-package/ ) || true"
        for file in APP_FILES
    )
    return (
        "rm -rf /tmp/lambda-package && "
        "pip install --target /tmp/lambda-package -r /var/task/requirements.txt "
        "--platform manylinux2014_x86_64 --only-binary=:all: && "
        "rm -rf /var/task/lambda-package && "
        "mkdir -p /var/task/lambda-package && "
        "cp -a /tmp/lambda-package/. /var/task/lambda-package/ && "
        f"{app_copy_steps} && "
        "if [ -d /var/task/data ]; then cp -r /var/task/data /var/task/lambda-package/; fi"
    )


def main():
    print("Creating Lambda deployment package...")

    if os.path.exists("lambda-deployment.zip"):
        os.remove("lambda-deployment.zip")

    # Install dependencies using Docker with Lambda runtime image
    print("Installing dependencies for Lambda runtime...")

    # Use the official AWS Lambda Python 3.13 image
    # This ensures compatibility with Lambda's runtime environment
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.getcwd()}:/var/task",
            "--platform",
            "linux/amd64",  # Force x86_64 architecture
            "--entrypoint",
            "",  # Override the default entrypoint
            "public.ecr.aws/lambda/python:3.13",
            "/bin/sh",
            "-c",
            build_docker_shell_command(),
        ],
        check=True,
    )

    # Create zip
    print("Creating zip file...")
    with zipfile.ZipFile("lambda-deployment.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda-package"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "lambda-package")
                zipf.write(file_path, arcname)

    # Show package size
    size_mb = os.path.getsize("lambda-deployment.zip") / (1024 * 1024)
    print(f"Created lambda-deployment.zip ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()