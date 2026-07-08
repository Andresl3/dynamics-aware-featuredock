# Download Model Weights

To access the model weights, we provide two options.

## From 🤗HuggingFace

Dyna-1 model weights (for both ESM-3 and ESM-2 versions) can be accessed through HuggingFace at <a href='https://huggingface.co/gelnesr/Dyna-1'>gelnesr/Dyna-1</a>. 

We recommend setting up and using `huggingface-cli` by running the following commands on the command line.

```
pip install -U "huggingface_hub[cli]"
huggingface-cli download gelnesr/Dyna-1 --local-dir "model/weights/"
```

Another option is to use the `git clone` to download, set the download directory to `model/weights`. This will require doing the following:

```
git lfs install
git clone git@hf.co:gelnesr/Dyna-1
```

More info on how to download the model from HuggingFace can be found <a href='https://huggingface.co/docs/hub/en/models-downloading'>here</a>.

## From Google Drive

Download the model weights for Dyna-1 with ESM3 <a href='https://drive.google.com/file/d/1UJWpPKPgJH9AYADMIqL0MzyU772CrP9t/view?usp=share_link'> here </a> and Dyna-1 with ESM2 <a href='https://drive.google.com/file/d/1YPzIouDXfalXSHAde-Ke5VWxlprz3rcV/view?usp=share_link'> here</a>. Then, upload them to the `model/weights` folder. 

You can download by using `gdown https://drive.google.com/file/uc?id=<google_code>`.
