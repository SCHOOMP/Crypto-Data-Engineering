# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


def grabData(name):
    import kagglehub

    # Download latest version
    path = kagglehub.dataset_download("mczielinski/bitcoin-historical-data")

    print("Path to dataset files:", path)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    grabData('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
