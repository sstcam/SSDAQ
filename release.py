import re
import os


def bump_version():
    with open("ssdaq/version.py") as f:
        s = f.read()
    m = re.search(r'__version__ = "(.*)\.(.*)\.(.*)"', s)
    v1, v2, v3 = m.groups()
    oldv = "{0}.{1}.{2}".format(v1, v2, v3)
    newv = "{0}.{1}.{2}".format(v1, v2, str(int(v3) + 1))
    print("Current version is: {0}, write new version, ctrl-c to exit".format(oldv))
    try:
        ans = input(newv)
        if ans:
            newv = ans
            ans = input("Change version to, %s?(Y/n)"%newv)
            if ans not in ("", "y", "yes"):
                print('Exiting...')
                raise KeyboardInterrupt

        s = s.replace(oldv, newv)
        with open("ssdaq/version.py", "w") as f:
            f.write(s)
    except KeyboardInterrupt:
        print("\nInterrupted, version not changed...")
        exit()
    return newv


def release():
    v = bump_version()
    ans = input("version bumped, commiting?(Y/n)")
    if ans in ("", "y", "yes"):
        os.system("git add ssdaq/version.py")
        os.system("git commit -m 'new release'")
        os.system("git tag {0}".format(v))
        ans = input("change committed, push to server?(Y/n)")
        if ans in ("", "y", "yes"):
            os.system("git push")
            os.system("git push --tags")
        # ans = input("upload to pip?(Y/n)")
        # if ans in ("", "y", "yes"):
        #     os.system("rm -rf dist/*")
        #     os.system("python setup.py sdist")
        #     os.system("twine upload dist/*")


if __name__ == "__main__":
    release()