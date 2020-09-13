LEVELS = ['native', 'studying', 'fluent']

class Files:
    # Statics
    class Static:
        __STATICS = 'static/'
        __CALENDAR_TEMPLATES = Files.Static.__STATICS + 'calendar_templates/'

        ANALYTICS = Files.Static.__STATICS + 'analytics.png'
        PROFILE = Files.Static.__STATICS + 'profile.png'

        CALENDAR_TEMPLATE = Files.Static.__CALENDAR_TEMPLATES + 'calendar_template.png'
        CALENDAR_TEMPLATE2 = Files.Static.__CALENDAR_TEMPLATES + 'calendar_template2.png'

    # Gifs
    class Gif:
        __GIF = 'gif/' # Abstracting useless attr
        """
        __data__ should look something like this:
        {   
            'native_germanic': '/gif/native/germanic.gif',
            'native_asian': '/gif/native/asian.gif',
            'fluent_asian': '/gif/fluent/asian.gif'
            '{level}_{name}': '/gif/{level}/{name}.gif'
        }
        """
        __data__ = {}


        @classmethod
        def get(cls, level, name): # 
            """
            Throws KeyError

            level: 'native' or 'studying' or 'fluent'
            """
            level = str.lower(level)
            if level in LEVELS:
                try:
                    return self.__data__[level+'_'+name]
                except KeyError:
                    raise
            else:
                raise KeyError("level:", level, "doesn't exist")

def __gifgen():
    try:
        import os
    except ImportError:
        print("Please use python >=3.6")

    for level in LEVELS:
        for filename in os.listdir(Files.Gif.__GIF + level):
            identifier_filename = filename.replace(".gif", "")
            Files.Gif.__data__[level+'_'+identifier_filename] = Files.Gif.__GIF + level + '/' +filename
    return True

try:
    __gifgen()
except Exception as e:
    print("Ignoring exception when generating Gif files \n{}".format(e))
    
