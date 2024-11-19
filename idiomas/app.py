from flask import Flask, request, jsonify, render_template
from elevenlabs import save, ElevenLabs
from openai import OpenAI
from dotenv import dotenv_values
import re
import os
from datetime import datetime


config = dotenv_values(".env")
ELEVENLABS_API_KEY = config.get("ELEVENLABS_API_KEY")
OPEANAI_API_KEY = config.get("OPENAI_API_KEY")

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

lista_nombres={}


def get_voices(client):
    try:
        response = client.voices.get_all()
        voces={}
        for voice in response.voices:
            if not voice.labels: 
                voice.labels['accent']='sin acento'

            lista_nombres[voice.name]=voice.voice_id
            voces[voice.voice_id]={'name':voice.name, 'accent':voice.labels['accent']}
      
        return voces
          
    except Exception as e:
        print(f"Error obteniendo las voces: {str(e)}")
        return {}

voices = get_voices(client) #obtener las voces disponibles



def get_dialogo(indicaciones,num_frases,ids):
    #obtener el dialogo de un prompt de openai
    client = OpenAI()

    num_personas=len(ids)
    nombres=""
    for id in ids:
        nombres+=voices[id]['name']+", "

    prompt = f"Generar un dialogo en inglés de {num_frases} frases entre {num_personas} personas, que sus nombres son {nombres}. Cada frase tiene al principio el nombre de la persona que interviene seguido de una almohadilla(#) y la frase de esa persona. Teniendo en cuenta esto: {indicaciones}. La salida sólo debe incluir las frases de las personas empezando por su nombre, y ningun otro texto. Ejemplo: Juan#Hola, como estas? Maria#Bien, gracias."

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un experto en idiomas."},
            {
                "role": "user",
                "content": prompt,
            }
        ]
    )

    return completion.choices[0].message.content


def concatenate_audios(generated_files, output_path="output_combined.mp3"):
    # Concatenar archivos binariamente
    with open(output_path, "wb") as outfile:
        for filename in generated_files:
            with open(filename, "rb") as infile:
                outfile.write(infile.read())
    print(f"Todos los audios han sido combinados en {output_path}")




app = Flask(__name__)

#devolver la vista index.html y pasarle la lista de voces
@app.route("/")
def index():
    return render_template("index.html", voices=voices)
 

@app.route("/generar_audio", methods=["POST"])
def generar_audio():
    output_dir = "generated_audios"
    dialogo = request.form.get("dialogo")  # Obtiene el valor de 'prompt'

    rutas_ficheros_creados=[]
    output_dir = "generated_audios"
    os.makedirs(output_dir, exist_ok=True)

    pos=0
    frases=dialogo.split("\n")
    for frase in frases:
        nombre, texto=frase.split("#")
        voice_id=lista_nombres[nombre]
        audio_content = client.generate(
            text=texto,
            voice=voice_id,
            model="eleven_multilingual_v2"
        )
        ruta= os.path.join(output_dir, f"{nombre}{pos}.mp3")
        save(audio_content, ruta)
        rutas_ficheros_creados.append(ruta)
        pos+=1

    concatenate_audios(rutas_ficheros_creados, "output_combined.mp3")

@app.route("/generar_dialogo", methods=["POST"])
def generar_dialogo():
    prompt = request.form.get("prompt")  # Obtiene el valor de 'prompt'
    voice_ids = request.form.getlist('voice_ids[]') 
    num_frases=request.form.get("num_frases")


    dialogo=get_dialogo(prompt,num_frases,voice_ids)

    return dialogo

# Ejecutar la aplicación Flask
if __name__ == "__main__":
    app.run(debug=True)

