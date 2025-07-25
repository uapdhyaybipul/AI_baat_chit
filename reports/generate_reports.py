from dotenv import load_dotenv
import google.generativeai as genai
import json
import re
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import io
from pydantic import BaseModel
from fastapi import FastAPI
import os
import uvicorn

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
Pie_image_path = os.getenv("Pie_image_path")
Recording_path = os.getenv("Recording_path")
Report_path = os.getenv("Report_path")
print(Recording_path)
app = FastAPI()


def find_json_in_string(input_string):
  print("Inside find_json_in_string finding json ")
  start_index = input_string.find("{")
  end_index = input_string.rfind("}")

  if start_index == -1 or end_index == -1 or start_index > end_index:
    return None  # No valid JSON object found

  json_string = input_string[start_index : end_index + 1]
  try:
    json_object = json.loads(json_string)
    return json_object
  except json.JSONDecodeError:
    return None  # Invalid JSON format
  

def find_json_and_remove(input_string):
  print("Inside find_json_and_remove cleaning text ")
  try:
    # Use a regular expression to find a valid JSON object
    match = re.search(r'(\{(?:[^{}]*)\}|\[(?:[^\[\]]*)\])', input_string)

    if match:
      json_string = match.group(0)
      try:
        json_object = json.loads(json_string)  # Validate that it's valid JSON
        cleaned_string = input_string.replace(json_string, "", 1)  # Remove only the first instance
        return cleaned_string, json_object
      except json.JSONDecodeError:
        return input_string, None  # Invalid JSON, return original string and None
    else:
      return input_string, None  # No JSON found, return original string and None

  except Exception as e:
    print(f"An error occurred: {e}")  # Handle potential exceptions more gracefully
    return input_string, None
  
def filter_scores(score_analysis):
  print("Inside filter_scores cleaning scores ")
  filtered_scores = {}
  for key, value in score_analysis.items():
    if 'score' in key:
      filtered_scores[key] = value
  return filtered_scores


def filtered_text(score_analysis):
  print("Inside filter_scores cleaning scores text ")
  filtered_text = {}
  for key, value in score_analysis.items():
    if 'Analysis' in key:
      filtered_text[key] = value
  return filtered_text



def pie_chart(filtered_scores):
  # Sample data (replace with your actual data)
  print("Inside pie_chart making piechart ")
  labels = list(filtered_scores.keys())
  sizes = [float(score.split('/')[0]) for score in filtered_scores.values()]

  # Create the pie chart
  plt.figure(figsize=(8, 6))
  plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, shadow = True, explode = (0.1, 0, 0,0))
  plt.axis('equal')
  plt.title('Scores')
  png_path = os.path.join(Pie_image_path,'pie_chart.png')
  plt.savefig(png_path) # Save the pie chart as a PNG image
  plt.close()
  return png_path


def generate_pdf(content, image_path, analysis_paragraph):
    print("inside generate_pdf generating pdf ")
    """Generates a PDF document with given content, image, and analysis."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Add the pie chart image
    img = Image(image_path, width=8 * inch, height=6 * inch)  # Adjust width and height as needed
    story.append(img)
    story.append(Spacer(1, 12))

    # Add the analysis paragraph
    story.append(Paragraph("<b>Analysis:</b>", styles['Normal']))
    story.append(Spacer(1, 6))
    story.append(Paragraph(analysis_paragraph, styles['Normal'])) #add analysis paragraph
    story.append(Spacer(1, 12))

    # Add the main content
    for line in content.split("\n"):
        if line.strip():
            story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 6))


    doc.build(story)
    buffer.seek(0)
    return buffer


class CallReportGeneration(BaseModel):
    recording_name : str

@app.post("/get_report_for_recordings")
def call_gemini(request:CallReportGeneration):
    # Initialize a Gemini model appropriate for your use case.
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-thinking-exp-01-21")
    recording_name = request.recording_name
    print(recording_name)
    #check if path exist or not
    file_path= os.path.join(Recording_path,recording_name)
    print("file_path",file_path)
    if file_path:
        myfile = genai.upload_file(file_path)   #Give audio file path
        # Create the prompt.
        prompt = """Generate a detaied transcript of the speech in English distinguishing b/w user and bot.Also give the a dteail summary in json
         {"confidence_score":"",
         "confidence_Analysis":"",

         "fluency_score":"",
         "fluency_Analysis":"",

         "communication_score":"",
         "communication_Analysis":"",

         "technical_score":"",
         "technical_Analysis":""
        }
        including confidence score,fluency score,communication score,technical_score by analysing user's voice on way of his talking and communication skills at the end of transcript"""

        # Pass the prompt and the audio file to Gemini.
        response = model.generate_content([prompt, myfile])

        # Print the transcript.
        print(response.text)

        #finding_Json
        json_data = find_json_in_string(response.text)
        print("mai hu json_data",json_data)
        cleaned_response, _ = find_json_and_remove(response.text)
        print("mai hu cleaned_response",cleaned_response)
        #filtering_scores
        filtered_scores = filter_scores(json_data)
        print("mai hu filtered score",filtered_scores)


        # Create the pie chart and save it as an image
        png_path = pie_chart(filtered_scores)


        # Create a paragraph from the analysis scores
        analysis_paragraph = ""
        for key, value in json_data.items():
            analysis_paragraph += f"<b>{key.replace('_Analysis','').capitalize()}:</b> {value}<br/>"

        # Correctly pass arguments to generate_pdf
        pdf_buffer = generate_pdf(cleaned_response, png_path, analysis_paragraph)

        #path for report
        recording_report_path = os.path.join(Report_path,f"{request.recording_name}_transcript.pdf")

        # Save the BytesIO buffer to a temporary file
        with open(recording_report_path, 'wb') as f:
            f.write(pdf_buffer.getbuffer())

        # Download the temporary file
        # files.download('transcript.pdf')

    else:
        return{"response":"no file founded","file_path":file_path}

    return {"response":response.text,"report_path":Report_path}
    
if __name__ == "__main__":
    uvicorn.run(app, port=5502)