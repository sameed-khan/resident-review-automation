**3/25**
- successful run to finished execution
- successful save to json file
- breaks when 'addendum' report pops up
    - solution: allow skipping of buttons in case of any error
    - inform user after analyzing completed data and output error output / skipped reads
- final output format
    - generate execution instructions
    - compute diff
    - figure out how that gets output (word doc? streamlit interface?)

**4/12**
- completed diff code
- big problem is that the script is going back and picking up the same outputs for both the attending and resident reads
    - all attending reads are the same as resident reads
    - need to double check this and see why the script off-clicking the buttons didn't work
