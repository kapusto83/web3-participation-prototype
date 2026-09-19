import streamlit as st


WALLET_HTML = """
<div>
    <button id="connect-wallet">Connect wallet</button>

    <button id="sign-acknowledgement" style="display:none;">
        Sign acknowledgement
    </button>

    <div id="wallet-status" style="margin-top:10px;"></div>
</div>
"""


WALLET_JS = """
export default function({ parentElement, setStateValue, data }) {

    const connectButton =
        parentElement.querySelector("#connect-wallet");

    const signButton =
        parentElement.querySelector("#sign-acknowledgement");

    const status =
        parentElement.querySelector("#wallet-status");

    let walletAddress = null;

    async function connectWallet() {

        if (!window.ethereum) {
            status.textContent =
                "No compatible browser wallet detected.";
            return;
        }

        try {

            status.textContent = "Connecting...";

            const accounts =
                await window.ethereum.request({
                    method: "eth_requestAccounts"
                });

            if (!accounts || accounts.length === 0) {
                throw new Error("No wallet account returned.");
            }

            walletAddress = accounts[0];

            setStateValue("wallet", {
                address: walletAddress
            });

            status.textContent =
                "Connected: " +
                walletAddress.slice(0, 6) +
                "..." +
                walletAddress.slice(-4);

            connectButton.style.display = "none";
            signButton.style.display = "inline-block";

        } catch (error) {

            status.textContent =
                "Connection failed: " + error.message;
        }
    }


    async function signAcknowledgement() {

        if (!walletAddress) {
            status.textContent =
                "Connect your wallet first.";
            return;
        }

        const message = data.message;

        try {

            status.textContent =
                "Waiting for wallet signature...";

            const signature =
                await window.ethereum.request({
                    method: "personal_sign",
                    params: [
                        message,
                        walletAddress
                    ]
                });

            setStateValue("signature", {
                address: walletAddress,
                message: message,
                signature: signature
            });

            status.textContent =
                "Acknowledgement signed.";

            signButton.style.display = "none";

        } catch (error) {

            status.textContent =
                "Signature cancelled or failed: " +
                error.message;
        }
    }


    connectButton.onclick = connectWallet;
    signButton.onclick = signAcknowledgement;
}
"""


def wallet_component(message: str):

    component = st.components.v2.component(
        name="wallet_connector",
        html=WALLET_HTML,
        js=WALLET_JS,
    )

    return component(
        data={"message": message},
        key="wallet_connector",
    )