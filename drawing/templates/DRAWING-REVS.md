# Drawing / model revision register

Rules: the model drives the rev letter and a drawing always carries its model's letter. Letters
start at A and skip I, L, O, Q (then AA, AB ...). Drawing-only clerical changes add .01, .02 ...;
a model change takes the next letter and resets the decimal. Redlines go on the drawing first,
then the model is fixed, then the drawing is regenerated. Rev A is only for a brand-new model;
an existing model's letter comes from counting its past releases (list them under Evidence).

| Item | Part no. | Model | Made with | Rev | Date | Change | Evidence (counted releases) | Files |
|---|---|---|---|---|---|---|---|---|
| <item> | <part no.> | `<path/to/model.step>` | <tool, e.g. build123d> | A | <YYYY-MM-DD> | Initial | new model | `<path/to/drawing.pdf>` |

## How the letters were found

| Part no. | Rev | Evidence |
|---|---|---|
| <part no.> | A | new model, first release |
