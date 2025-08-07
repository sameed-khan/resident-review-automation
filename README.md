# Resident Review Automation Project

Intended to speed up reviewing inside Sectra PACS interface by automating opening and closing of
attending-reviewed reports.

## Instructions
1. Download the .zip file from the 'Releases' page on Github.
2. Open Fluency / MModal and pull up the selected studies that you want to extract on the screen on your *right side*.
    * The script assumes that you are using a 3-monitor setup and that the relevant reads are on the right
3. Click the 'Advanced Search' and enter in the complete range of studies you would like the script to run through.
4. Right-click `setup.ps1` and select *Run with Powershell*.
    * You may need to click through a few dialogue prompts and confirm that you want to run the script.
    * If the script errors out early, try running it again.
5. The script will go ahead and extract the relevant reports.
6. You should find the completed output in the final *output.docx*.

## Handling Errors
1. If the script pauses and does not continue (running in loop), you will usually see similar logging repeated over and over on the command line
    a. Press Alt+F4 to close the report window
    b. The script should pick up where it left off
2. If the above doesn't work, *click the command line window* (labeled Windows Powershell at the top) and press Ctrl + C. The script does take mouse control, so if clicking is difficult, you can also use Alt + Tab to shift focus over to the Powershell screen and then hit Ctrl + C. 