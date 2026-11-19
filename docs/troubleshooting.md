# Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| **Not answering** | No check has reached the Bundesbank's web service | Check the deployment's outbound access to api.statistiken.bundesbank.de; the plugin tries again within the hour |
| **Answering**, with a warning | An earlier check worked; the last did not (the web service sometimes asks to retry while it prepares an answer) | Nothing, usually: the next check runs within the hour |
| **1 record not held** | Your deployment holds no record for the Bund curve: the platform does not seed it yet | Nothing the plugin can do: it never makes a record. Its values are recorded once your deployment holds it |
| A day declined, *source silent* | A weekend, a holiday, a day not published yet | Wait for the Bundesbank's next publication |
| A subject declined, *not covered* | Not this plugin's record | Check the Records tab |
| Datasets: **Not licensed yet** | No deployment admin has licensed the dataset | Ask a deployment admin to license it on Data sources |
