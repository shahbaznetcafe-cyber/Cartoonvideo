import sys
sys.stdout.reconfigure(encoding="utf-8")
def main():
    import config, story_parser, build
    config.STORY_MODE="blender3d"; config.CAPTIONS["enabled"]=False; config.ASPECT="landscape"
    manual={"title":"Sabzi Bazaar 3D","language":"roman_urdu",
      "characters":[{"id":"tamatar","name":"Tamatar","gender":"male","role":"tomato"},
                    {"id":"gajar","name":"Gajar","gender":"male","role":"carrot"}],
      "scenes":[{"id":1,"location":"vegetable market","mood":"comedy",
        "background_prompt":"a cartoon vegetable market stall",
        "lines":[{"speaker":"tamatar","text":"Bazaar mein aaj bohat raunaq hai!","emotion":"happy","action":""},
                 {"speaker":"gajar","text":"Haan bhai, sab sabziyan taaza hain!","emotion":"happy","action":""}]}]}
    story_parser.parse_script=lambda s: story_parser._assign_voices(manual)
    r=build.build("(bypass)",proj_name="test3d_market",on_progress=lambda st,i,t,m:print(f"[{st}] {m}",flush=True))
    print("RESULT:",r)
if __name__=="__main__": main()
