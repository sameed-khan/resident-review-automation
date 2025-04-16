# Resident Review Automation Project

Intended to speed up reviewing inside Sectra PACS interface by automating opening and closing of
attending-reviewed reports.

## Instructions
1. Download the .zip file
2. Open Fluency / MModal and pull up the selected studies that you want to extract on the screen on your *right side*.
    * The script assumes that you are using a 3-monitor setup and that the relevant reads are on the right
3. Right-click `setup.ps1` and select *Run with Powershell*.
    * You may need to click through a few dialogue prompts and confirm that you want to run the script.
    * If the script errors out early, try running it again.
4. The script will go ahead and extract the relevant reports.
5. You should find the completed output in the final *output.docx*.
