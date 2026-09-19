export default async function handler(req, res) {
    const code = req.query.code;
    const state = req.query.state;

    if (!code || !state) {
        return res.status(400).send("Missing OAuth code or state.");
    }

    try {
        const response = await fetch(
            "https://warranties-tube-methods-pill.trycloudflare.com/oauth/complete",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Helix-Secret": process.env.HELIX_CALLBACK_SECRET
                },
                body: JSON.stringify({
                    code,
                    state
                })
            }
        );

        if (!response.ok) {
            console.error(
                "Helix returned:",
                response.status,
                await response.text()
            );

            return res.status(500).send(
                "Verification could not be completed."
            );
        }

        return res.status(200).send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Helix Verification</title>
            </head>
            <body>
                <h1>Roblox Account Linked</h1>
                <p>Your Roblox account has been successfully linked.</p>
                <p>You can now return to Discord.</p>
            </body>
            </html>
        `);

    } catch (error) {
        console.error(error);

        return res.status(500).send(
            "Could not connect to Helix."
        );
    }
}
