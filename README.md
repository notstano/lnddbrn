# What?
A small tool that displays the amount of burned Skybreach Land Deeds, by type.

It also displays the Top 10 used EVM addresses. 

And it provides a search field, e.g. to check for your address. 
(**Note** that the data is refreshed **manually** so it may take time before your transaction is 
considered for the UI, do not panic. If in doubt, the recommended way is to check your extrinsics on Subscan.)

# How?
* Subscrape is used to fetch `utility.batch_all` extrinsic transactions from Subscan
  * tracked in a separate branch since I can't properly install Subscrape as a dependency and I'm hesitant to merge to main until I'm sure it won't break the Streamlit app
  * the Subscrape script is ran manually and the data is uploaded manually for the App to use
    * therefore the displayed stats may not be fresh
* Streamlit is used to build the UI
* Simple matplotlib plots