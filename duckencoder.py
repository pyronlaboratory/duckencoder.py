#!/usr/bin/env python
from __future__ import print_function
import time
import sys
import getopt
import os

class DuckEncoder:
        @staticmethod
        def readResource(filename):
                """
                Reads a resource file and creates a dictionary with key-value pairs
                based on lines of the file, removing comments, line breaks, and
                empty lines. It then returns the resulting dictionary.

                Args:
                    filename (str): name of the file that contains the data to be
                        read and processed by the function.

                Returns:
                    dict: a dictionary containing the key-value pairs obtained
                    from parsing the given file.

                """
                result_dict = {}
                lines = []
                with open(filename, "r") as f:
                        lines = f.readlines()
                for l in lines:
                        # remove comment from line
                        l = l.split("//")[0]
                        # remove line breaks
                        l = l.strip().replace("\r\n", "").replace("\n", "")

                        # skip empty lines
                        if len(l) == 0:
                                continue

                        key, val = l.split("=", 1)
                        result_dict[key.strip()] = val.strip()

                return result_dict

        @staticmethod
        def parseScriptLine(line, keyProp, langProp):
                """
                parses a script line and returns the corresponding USB bytes or
                an empty string if no match is found. It handles various commands
                like CTRL-C, CTRL-V, ALT-TAB, and others, as well as direct key inputs.

                Args:
                    line (str): input line being processed, which allows the
                        function to interpret and encode different types of keyboard
                        input commands based on their specific format and structure.
                    keyProp (dict): 16-bit USB property value that contains the
                        keycode information for the current keyboard layout, which
                        is used to map the encoded command to the corresponding
                        USB byte values.
                    langProp (str): 2-letter language code for the keyboard layout
                        and is used to encode the input string as USB byte values
                        based on the selected keyboard layout.

                Returns:
                    : USB bytes.: a USB byte array representing a single keyboard
                    input, based on the script line provided.
                    
                    	1/ `result`: This is the actual encoded USB command that will
                    be sent to the keyboard. It is a bytearray representing the
                    USB hexadecimal code for the key combination specified in the
                    input string.
                    	2/ `cmd`: This variable contains the command or key combination
                    that was given as input. It can take on various values, such
                    as "MODIFIERKEY", "KEY", "ALT-SHIFT", etc., depending on the
                    input string.
                    	3/ `args`: This variable contains any additional arguments
                    provided after the key combination, if applicable. For example,
                    if the input was "MODIFIERKEY_LEFT_CTRL+ALT", then `args` would
                    contain the string "ALT".
                    	4/ `keyProp`: This variable contains the property name of the
                    keyboard key that corresponds to the key combination specified
                    in the input string. For example, if the input was
                    "MODIFIERKEY_LEFT_CTRL", then `keyProp` would be "MODIFIERKEY_LEFT_CTRL".
                    	5/ `langProp`: This variable contains the language property
                    name of the keyboard key that corresponds to the key combination
                    specified in the input string. For example, if the input was
                    "MODIFIERKEY_LEFT_CTRL", then `langProp` would be "MODIFIERKEY".
                    
                    	In summary, the `parseScriptLine` function takes a script
                    line as input and returns an encoded USB command that can be
                    sent to a keyboard to execute the specified key combination
                    or command. The output of the function has various properties
                    and attributes that can be useful in handling different cases
                    and scenarios.

                """
                result = ""

                # split line into command and arguments
                cmd, _, args = line.partition(" ")
                cmd = cmd.strip()
                args = args.strip()

                # DELAY (don't check if second argument is present and int type)
                if cmd == "DELAY":
                        delay = int(args)
                        result = DuckEncoder.delay2USBBytes(delay)

                # STRING
                elif cmd == "STRING":
                        if not args:
                                return ""
                        # for every char
                        for c in args:
                                keydata = DuckEncoder.ASCIIChar2USBBytes(c, keyProp, langProp)
                                if len(keydata) > 0:
                                        result += keydata

                # STRING_DELAY
                elif cmd == "STRING_DELAY":
                        if not args:
                                return ""

                        # split away delay argument from remaining string
                        delay, chars = args.split(" ", 1)

                        # build delaystr
                        delay = int(delay.strip())
                        delaystr = DuckEncoder.delay2USBBytes(delay)

                        # for every char
                        for c in chars.strip():
                                keydata = DuckEncoder.ASCIIChar2USBBytes(c, keyProp, langProp)
                                if len(keydata) > 0:
                                        result += keydata + delaystr

                elif cmd in ("CONTROL", "CTRL"):
                        # check if second argument after CTRL / Control
                        if args:
                                # given key with CTRL modifier
                                result = (DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp) +
                                          DuckEncoder.prop2USBByte("MODIFIERKEY_CTRL", keyProp, langProp))
                        else:
                                # left CTRL without modifier
                                result = DuckEncoder.prop2USBByte("KEY_LEFT_CTRL") + "\x00"

                elif cmd == "ALT":
                        # check if second argument after  ALT
                        if args:
                                # given key with CTRL modifier
                                result = (DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp) +
                                          DuckEncoder.prop2USBByte("MODIFIERKEY_ALT", keyProp, langProp))
                        else:
                                # left ALT without modifier
                                result = DuckEncoder.prop2USBByte("KEY_LEFT_ALT") + "\x00"

                elif cmd == "SHIFT":
                        # check if second argument after  ALT
                        if args:
                                # given key with CTRL modifier
                                result = (DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp) +
                                          DuckEncoder.prop2USBByte("MODIFIERKEY_SHIFT", keyProp, langProp))
                        else:
                                # left SHIFT without modifier
                                result = DuckEncoder.prop2USBByte("KEY_LEFT_SHIFT") + "\x00"

                elif cmd == "CTRL-ALT":
                        # check if second argument after CTRL+ ALT
                        if args:
                                # key
                                result += DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp)
                                # modifier for CTRL and ALT or'ed  together
                                result += chr(ord(DuckEncoder.prop2USBByte("MODIFIERKEY_CTRL", keyProp, langProp)) |
                                              ord(DuckEncoder.prop2USBByte("MODIFIERKEY_ALT", keyProp, langProp)))
                        else:
                                return ""

                elif cmd == "CTRL-SHIFT":
                        # check if second argument after CTRL+ SHIFT
                        if args:
                                # key
                                result += DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp)
                                # modifier for CTRL and SHIFT or'ed  together
                                result += chr(ord(DuckEncoder.prop2USBByte("MODIFIERKEY_CTRL", keyProp, langProp)) |
                                              ord(DuckEncoder.prop2USBByte("MODIFIERKEY_SHIFT", keyProp, langProp)))
                        else:
                                return ""

                elif cmd == "COMMAND-OPTION":
                        # check if second argument after CTRL+ SHIFT
                        if args:
                                # key
                                result += DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp)
                                # modifier for CTRL and SHIFT or'ed  together
                                result += chr(ord(DuckEncoder.prop2USBByte("MODIFIERKEY_LEFT_GUI", keyProp, langProp)) |
                                              ord(DuckEncoder.prop2USBByte("MODIFIERKEY_ALT", keyProp, langProp)))
                        else:
                                return ""

                elif cmd == "ALT-SHIFT":
                        # check if second argument after CTRL+ SHIFT
                        if args:
                                # key
                                result += DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp)
                                # modifier for CTRL and SHIFT or'ed  together
                                result += chr(ord(DuckEncoder.prop2USBByte("MODIFIERKEY_LEFT_ALT", keyProp, langProp)) |
                                              ord(DuckEncoder.prop2USBByte("MODIFIERKEY_SHIFT", keyProp, langProp)))
                        else:
                                # key
                                result += DuckEncoder.prop2USBByte("KEY_LEFT_ALT", keyProp, langProp)
                                # modifier for CTRL and SHIFT or'ed  together
                                result += chr(ord(DuckEncoder.prop2USBByte("MODIFIERKEY_LEFT_ALT", keyProp, langProp)) |
                                              ord(DuckEncoder.prop2USBByte("MODIFIERKEY_SHIFT", keyProp, langProp)))

                elif cmd == "ALT-TAB":
                        # check if second argument after CTRL+ SHIFT
                        if args:
                                return ""
                        else:
                                # key
                                result += DuckEncoder.prop2USBByte("KEY_TAB", keyProp, langProp)
                                # modifier for CTRL and SHIFT or'ed  together
                                result += DuckEncoder.prop2USBByte("MODIFIERKEY_LEFT_ALT", keyProp, langProp)

                elif cmd in ("GUI", "WINDOWS"):
                        # check if second argument after  ALT
                        if args:
                                # given key with CTRL modifier
                                result = (DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp) +
                                          DuckEncoder.prop2USBByte("MODIFIERKEY_LEFT_GUI", keyProp, langProp))
                        else:
                                # left SHIFT without modifier
                                result = (DuckEncoder.prop2USBByte("KEY_LEFT_GUI", keyProp, langProp) +
                                          DuckEncoder.prop2USBByte("MODIFIERKEY_LEFT_GUI", keyProp, langProp))

                elif cmd == "COMMAND":
                        # check if second argument after  ALT
                        if args:
                                # given key with CTRL modifier
                                result = (DuckEncoder.keyInstr2USBBytes(args, keyProp, langProp) +
                                          DuckEncoder.prop2USBByte("MODIFIERKEY_LEFT_GUI", keyProp, langProp))
                        else:
                                # left SHIFT without modifier
                                result = DuckEncoder.prop2USBByte("KEY_COMMAND", keyProp, langProp) + "\x00"

                else:
                        # Everything else is handled as direct key input (worst case would be the first letter of a line interpreted as single key)
                        result = DuckEncoder.keyInstr2USBBytes(cmd, keyProp, langProp) + "\x00"

                return result

        @staticmethod
        def prop2USBByte(prop, keyProp, langProp):
                """
                converts a property (prop), a language-specific keycode for that
                property (keyProp), and a language-specific value for the property
                (langProp) into a binary string character representing the byte
                key or modifier value.

                Args:
                    prop (int): 0-based index of a keycode entry in a lookup table
                        for both key and language codes.
                    keyProp (`object`.): dictionary containing possible key codes
                        and their corresponding values, which is consulted by the
                        function to find the value for a given property.
                        
                        		- `prop`: This is the property being checked against the
                        `keyProp` dictionary.
                        		- `keyProp`: This is the dictionary containing keycodes
                        for different keys. It can contain various properties or
                        attributes such as:
                        		+ `prop`: The keycode value associated with the given
                        `prop` property.
                        		+ `langProp`: A dictionary of language-specific keycodes
                        for the same `prop`.
                        
                        	When checking against `keyProp`, the function first checks
                        if `prop` exists in `keyProp`. If it does, it retrieves
                        the corresponding keycode value from `keyProp` and converts
                        it to a binary string character. If `prop` is not found
                        in `keyProp`, it checks if `prop` exists in `langProp`.
                        If it does, it retrieves the language-specific keycode
                        value from `langProp` and converts it to a binary string
                        character. Finally, if neither `keyProp` nor `langProp`
                        contain an entry for `prop`, the function prints an error
                        message and returns an empty string.
                    langProp (dict): language-specific property values for the
                        given `prop` key, which are used to look up the corresponding
                        binary string character value when `prop` is not found in
                        the `keyProp`.

                Returns:
                    int: a binary string character representing the converted
                    keycode or modifier value.

                """
                if prop in keyProp:
                        keyval = keyProp[prop]
                elif prop in langProp:
                        keyval = langProp[prop]

                if keyval is None:
                        print("Error: No keycode entry for {0}".format(prop))
                        print("Warning this could corrupt generated output file")
                        return ""
                if keyval[0:2].upper() == "0X":
                        # conver to int from hex
                        keyval = int(keyval, 16)
                else:
                        # convert to int
                        keyval = int(keyval)

                # convert byte key / modifier value to binary string character
                return chr(keyval)

        # converts a delay given as interger to payload bytes
        @staticmethod
        def delay2USBBytes(delay):
                """
                takes a delay time in milliseconds as input and generates a series
                of bytes representing the remaining time until the next USB frame,
                with the least significant bit set to 1 if there is no remaining
                time, and otherwise set to 0.

                Args:
                    delay (int): 8-bit binary data to be converted into USB bytes.

                Returns:
                    str: a binary string consisting of a series of alternating 0s
                    and Fs, followed by a single character representing the remaining
                    portion of the delay value.

                """
                result = ""
                count = delay / 255
                remain = delay % 255
                for i in range(count):
                        result += "\x00\xFF"
                result += "\x00" + chr(remain)
                return result

        # returns USB key byte and modifier byte for the given partial single key instruction
        @staticmethod
        def keyInstr2USBBytes(keyinstr, keyProp, langProp):
                ####
                # Language fix
                # - a key instruction which is only 1 char in length, is represented as single ASCII char
                # - for example <CTRL>+<Z> in GERMAN has to be translated to MODIFIER_CTRL + KEY_Y
                # - but if "CONTROL z" would be given the current code translates to MODIFIER_CTRL + KEY_Z
                # - to account for this, we build the key instruction like ASCII translation, but remove the modifiers
                # thus bot, 'Z' and 'z' should become KEY_Y for German language layout
                #####
                """
                takes a key instruction and language property as input, translates
                it into a valid USB byte value using a look-up table, and returns
                the resulting value.

                Args:
                    keyinstr (str): 1-character key instruction to be translated
                        into a USB byte value, and its length is verified to ensure
                        it contains only a single ASCII character.
                    keyProp (dict): 16-bit code of the keyboard layout's property
                        dictionary for the currently active layout, which contains
                        the translation between the user's input and the corresponding
                        keycode value.
                    langProp (str): 2D array of keyboard shortcuts for different
                        languages, which is used to map the original key instruction
                        to the appropriate modifier and key combination for each
                        language layout.

                Returns:
                    ASCII character.: a binary string character representing a USB
                    keyboard key or modifier value.
                    
                    		- `keyval`: A variable that holds the translated USB byte
                    value for the given key instruction, or `None` if no matching
                    entry is found in either the keyboard or language properties.
                    		- `key_entry`: A string representing the raw key instruction
                    entered by the user, which is used as a starting point for the
                    translation process.
                    		- `keyProp`: A dictionary that contains mappings between raw
                    key instructions and their corresponding USB byte values for
                    the current keyboard layout.
                    		- `langProp`: A dictionary that contains mappings between
                    raw key instructions and their corresponding USB byte values
                    for different languages or layouts.
                    
                    	The function takes into account various aspects of the input
                    key instruction, such as:
                    
                    		- Length: If the input key instruction is a single character,
                    it is translated directly to an ASCII code, which is then
                    converted to a USB byte value using the `ASCIIChar2USBBytes`
                    function.
                    		- Modifiers: The function takes into account the presence
                    of modifier keys (such as Control, Alt, or Shift) and translates
                    them accordingly based on their associated values in the
                    `keyProp` dictionary.
                    		- Language: If the input key instruction is not present in
                    either the keyboard or language properties, it is translated
                    to the closest matching entry based on the language properties
                    using the `langProp` dictionary.

                """
                keyval = None
                key_entry = ""
                if len(keyinstr) == 1:
                        keyval = DuckEncoder.ASCIIChar2USBBytes(keyinstr, keyProp, langProp)[0]
                        return keyval
                else:
                        key_entry = "KEY_" + keyinstr.strip()

                # check keyboard property (first attempt)
                if key_entry in keyProp:
                        keyval = keyProp[key_entry]
                elif key_entry in langProp:
                        keyval = langProp[key_entry]

                # try to translate into valid KEY, if no hit on first attempt
                if keyval is None:
                        keyinstr = keyinstr.strip().upper()
                        keyinstr = {"ESCAPE": "ESC",
                                    "RETURN": "ENTER",
                                    "DEL": "DELETE",
                                    "BREAK": "PAUSE",
                                    "CONTROL": "CTRL",
                                    "DOWNARROW": "DOWN",
                                    "UPARROW": "UP",
                                    "LEFTARROW": "LEFT",
                                    "RIGHTARROW": "RIGHT",
                                    "MENU": "APP",
                                    "WINDOWS": "GUI",
                                    "PLAY": "MEDIA_PLAY_PAUSE",
                                    "PAUSE": "MEDIA_PLAY_PAUSE",
                                    "STOP": "MEDIA_STOP",
                                    "MUTE": "MEDIA_MUTE",
                                    "VOLUMEUP": "MEDIA_VOLUME_INC",
                                    "VOLUMEDOWN": "MEDIA_VOLUME_DEC",
                                    "SCROLLLOCK": "SCROLL_LOCK",
                                    "NUMLOCK": "NUM_LOCK",
                                    "CAPSLOCK": "CAPS_LOCK"}.get(keyinstr)

                        # second attempt
                        if keyinstr:
                                key_entry = "KEY_" + keyinstr.strip()
        
                                if key_entry in keyProp:
                                        keyval = keyProp[key_entry]
                                elif key_entry in langProp:
                                        keyval = langProp[key_entry]

                if keyval is None:
                        # avoid prints to STDOUT, which could be carried over raw data
                        sys.stderr.write("Error: No keycode entry for " + key_entry + "\n")
                        sys.stderr.write("Warning this could corrupt generated output file\n")
                        return ""
                if keyval[0:2].upper() == "0X":
                        # conver to int from hex
                        keyval = int(keyval, 16)
                else:
                        # convert to int
                        keyval = int(keyval)

                # convert byte key / modifier value to binary string character
                return chr(keyval)

        # returns USB key byte and modifier byte for the given ASCII key as binary String
        # Layout translation is done by the value given by langProp
        @staticmethod
        def ASCIIChar2USBBytes(char, keyProp, langProp):
                """
                converts an ASCII character to a USB byte value used for keyboard
                mapping. It retrieves the character's hexadecimal code and translates
                it into a name used in a language property file. The function then
                checks if the translated name exists in the language property file
                and maps its corresponding keycode or modifier value to a binary
                string character.

                Args:
                    char (int): 8-bit ASCII character value that needs to be
                        translated into its corresponding keyboard property entry
                        name in the target language.
                    keyProp (str): dictionary of keyboard property entries used
                        for translating character values into binary strings for
                        the chosen language, which is referenced in determining
                        the appropriate keyboard property entry for each character
                        value.
                    langProp (str): language property file, which maps character
                        codes to their corresponding keyboard layouts and modifier
                        keys.

                Returns:
                    str: a binary string representing a USB byte value based on
                    an ASCII character value and language property file entries.

                """
                result = ""
                # convert ordinal char value to hex string
                val = ord(char)
                hexval = str(hex(val))[2:].upper()
                if len(hexval) == 1:
                        hexval = "0" + hexval

                # translate into name used in language property file (f.e. ASCII_2A)
                name = ""
                if val < 0x80:
                        name = "ASCII_" + hexval
                else:
                        name = "ISO_8859_1_" + hexval

                # check if name  present in language property file
                if name not in langProp:
                        print(char + " interpreted as " + name + ", but not found in chosen language property file. Skipping character!")
                else:
                        # if name, parse values (names of keyboard property entries) in language property file
                        for key_entry in langProp[name].split(","):
                                keyval = None
                                key_entry = key_entry.strip()
                                # check keyboard property
                                if key_entry in keyProp:
                                        keyval = keyProp[key_entry]
                                elif key_entry in langProp:
                                        keyval = langProp[key_entry]
                                if keyval is None:
                                        print("Error: No keycode entry for " + key_entry)
                                        print("Warning this could corrupt generated output file")
                                        return ""
                                # convert to int from hex or base 10
                                keyval = int(keyval, 16) if keyval[0:2].upper() == "0X" else int(keyval)

                                # convert byte key / modifier value to binary string character
                                result += chr(keyval)
                        # check if modifier has been added
                        if len(result) == 1:
                                result += "\x00"
                return result

        @staticmethod
        def parseScript(source, keyProp, langProp):
                """
                splits a script into individual lines, skips blank lines and
                comments, and repeats an instruction with a specified number. It
                then appends each parsed line to a result string using the
                `DuckEncoder.parseScriptLine()` function.

                Args:
                    source (str): 1000+ lines of script written by the customer
                        that the code is intended to parse and return the resulting
                        encoded representation of the script.
                    keyProp (str): property key used for encoding and decoding.
                    langProp (str): language of the script to be parsed, and is
                        used to modify the behavior of the `DuckEncoder.parseScriptLine()`
                        function call for each line of the script.

                Returns:
                    str: a concatenation of parsed script lines from the input
                    source code.

                """
                result = ""
                lines = source.splitlines(True)

                lastLine = None
                for l in lines:
                        # remove leading whtespace and any line breaks
                        l = l.strip().replace("\r\n", "").replace("\n", "")

                        # skip blank lines and comments
                        if len(l) == 0 or l.startswith("//") or l.startswith("REM "):
                                continue

                        # check for repeat instruction
                        if l[0:7] == "REPEAT ":
                                # check for second arg and presence of las instruction
                                instr = l.split(" ", 1)
                                if len(instr) == 1 or lastLine is None:
                                        # second arg missing
                                        continue
                                else:
                                        for i in range(int(instr[1].strip())):
                                                result += DuckEncoder.parseScriptLine(lastLine, keyProp, langProp)
                        else:
                                result += DuckEncoder.parseScriptLine(l, keyProp, langProp)

                        lastLine = l

                return result

        @staticmethod
        def pwd():
                return os.path.dirname(__file__) or "."

        @staticmethod
        def generatePayload(source, lang):
                # check if language file exists
                """
                parses a given code snippet and uses a combination of property
                files to generate a payload based on the provided language.

                Args:
                    source (str): code that needs to be formatted and processed
                        by the `generatePayload()` function.
                    lang (str): language code for which the payload will be generated.

                Returns:
                    str: a parse tree representing the source code, constructed
                    from the language file and keyboard script.

                """
                script_dir = DuckEncoder.pwd()
                keyboard = DuckEncoder.readResource(script_dir + "/resources/keyboard.properties")
                language = DuckEncoder.readResource(script_dir + "/resources/" + lang + ".properties")

                payload = DuckEncoder.parseScript(source, keyboard, language)
                return payload

        def out2hid(self, data):
                """
                writes 8-bit binary data from a Python list to a USB HID device
                at a specified baud rate. It reads each 8-bit value from the list
                and generates an appropriate response, delaying between key presses
                if necessary.

                Args:
                    data (str): 8-bit byte sequence to be converted into HID inputs.

                """
                import time
                with open("/dev/hidg0", "wb") as f:
                        for i in range(0, len(data), 2):
                                out = ""
                                key = ord(data[i:i + 1])
                                if len(data[i + 1:i + 2]) == 0:  # no modifier byte
                                        continue
                                mod = ord(data[i + 1:i + 2])
                                if (key == 0):
                                        # delay code
                                        d = float(mod) / 1000.0
                                        time.sleep(d)
                                out = chr(mod) + '\x00' + chr(key) + '\x00\x00\x00\x00\x00' + '\x00\x00\x00\x00\x00\x00\x00\x00'
                                f.write(out)
                                f.flush()
                                # no delay between keypresses (hanfled by HID gadget)
                                # time.sleep(0.01)

        def outhidString(self, str):
                """
                converts a given string into an USB HID payload and sends it to
                the receiver through the `out2hid` method.

                Args:
                    str (str): 16-bit Unicode string that is converted into a USB
                        byte payload using DuckEncoder.ASCIIChar2USBBytes and then
                        transmitted to the host.

                """
                payload = ""
                for c in str:
                        payload += DuckEncoder.ASCIIChar2USBBytes(c, self.keyboard, self.language)
                self.out2hid(payload)

        def outhidStringDirect(self, str):
                """
                writes a string to USB HID device "/dev/hidg0" using DuckEncoder
                ASCII character encoding. It takes a string as input and produces
                output with modifier bytes added to each key press.

                Args:
                    str (str): 8-bit string that will be encoded and written to
                        the USB device.

                """
                with open("/dev/hidg0", "wb") as f:
                        for c in str:
                                data = DuckEncoder.ASCIIChar2USBBytes(c, self.keyboard, self.language)
                                for i in range(0, len(data), 2):
                                        out = ""
                                        key = ord(data[i:i + 1])
                                        if len(data[i + 1:i + 2]) == 0:  # no modifier byte
                                                continue
                                        mod = ord(data[i + 1:i + 2])
                                        if (key == 0):
                                                # delay code
                                                d = float(mod) / 1000.0
                                                time.sleep(d)
                                        out = chr(mod) + '\x00' + chr(key) + '\x00\x00\x00\x00\x00' + '\x00\x00\x00\x00\x00\x00\x00\x00'
                                        f.write(out)
                                f.flush()

        def outhidDuckyScript(self, source):
                """
                takes a source string and converts it into an encoded paylaod using
                the `DuckEncoder` class, then decodes and outputs the resulting
                hidable payload to the console.

                Args:
                    source (str): Python script to be encoded and passed through
                        the DuckEncoder for processing.

                """
                payload = DuckEncoder.parseScript(source, self.keyboard, self.language)
                self.out2hid(payload)
                # return payload

        def setLanguage(self, str_lang):
                """
                sets the language of the program based on a user-provided string,
                using the `DuckEncoder.readResource()` method to read and set the
                appropriate language file.

                Args:
                    str_lang (str): language to be set for the current DuckEncoder
                        instance, which the function then sets as its internal
                        property value.

                Returns:
                    str: a message indicating that the language has been set to
                    the specified value.

                """
                res = ""
                if self.__str_lang != str_lang:
                        try:
                                self.language = DuckEncoder.readResource(DuckEncoder.pwd() + "/resources/" + str_lang + ".properties")
                        except IOError:
                                res = "No language file for '{0}', resetting to 'us'".format(str_lang)
                                self.print_debug(res)
                                self.language = DuckEncoder.readResource(DuckEncoder.pwd() + "/resources/us.properties")
                                return res
                        self.__str_lang = str_lang
                        res = "language set to '{0}'".format(str_lang)
                        self.print_debug(res)
                        return res

        def getLanguage(self):
                return self.__str_lang

        def setKeyDevFile(self, key_dev_file):
                self.__key_dev_file = key_dev_file

        def print_debug(self, str):
                """
                has a single argument `str`, which is a string that will be printed
                to the console when the `self.DEBUG` flag is set.

                Args:
                    str (str): string to be printed as part of the debugging process
                        when the `self.DEBUG` flag is enabled.

                """
                if self.DEBUG:
                        print(str)

        def __init__(self, lang="us", key_dev_file="/dev/hidg0"):
                """
                sets properties for a `DuckEncoder` object, including a flag for
                debugging and resource files for keyboard layouts based on user
                language preference and device file location.

                Args:
                    lang (str): language of the keyboard layout for the DuckEncoder's
                        documentation.
                    key_dev_file (str): file where the keyboard layout is stored.

                """
                self.DEBUG = False
                self.keyboard = DuckEncoder.readResource(DuckEncoder.pwd() + "/resources/keyboard.properties")
                self.__key_dev_file = key_dev_file
                self.__str_lang = ""
                self.setLanguage(lang)


def usage():
        """
        defines and prints a usage message for a Python script that encodes
        DuckyScript source files to output files using the DuckEncoder tool. It
        provides options for input file, output file, keyboard layout, and enables
        passthru or raw passthru mode.

        """
        usagescr = '''Duckencoder python port 1.0 by MaMe82
=====================================

Creds to:       hak5Darren for original duckencoder
                https://github.com/hak5darren/USB-Rubber-Ducky

Converts payload created by DuckEncoder to sourcefile for DigiSpark Sketch
Extended to pass data from stdin to stdout

Usage: python duckencoder.py -i [file ..]                       Encode DuckyScript source given by -i file
   or: python duckencoder.py -i [file ..] -o [outfile ..]       Encode DuckyScript source to outputfile given by -o

Arguments:
   -i [file ..]         Input file in DuckyScript format
   -o [file ..]         Output File for encoded payload, defaults to inject.bin
   -l <layout name>     Keyboard Layout (us/fr/pt/de ...)
   -p, --pastthru       Read script from stdin and print result on stdout (ignore -i, -o)
   -r, --rawpassthru    Like passthru, but input is read as STRING instead of duckyscript
   -h                   Print this help screen
'''
        print(usagescr)


def main(argv):
        '''
        Parses command line
        '''
        script_dir = os.path.dirname(__file__) or "."

        ifile = ""
        source = None
        ofile = "inject.bin"
        lang = "us"
        rawpassthru = False
        try:
                opts, args = getopt.getopt(argv, "hi:o:l:pr", ["help", "input=", "output=", "language=", "passthru", "rawpassthru"])
        except getopt.GetoptError:
                usage()
                sys.exit(2)
        for opt, arg in opts:
                if opt in ("-h", "--help"):
                        usage()
                        sys.exit()
                elif opt in ("-i", "--input"):
                        ifile = arg
                        if not os.path.isfile(ifile) or not os.access(ifile, os.R_OK):
                                print("Input file " + ifile + " doesn't exist or isn't readable")
                                sys.exit(2)
                        with open(ifile, "rb") as f:
                                source = f.read()
                elif opt in ("-l", "--language"):
                        lfile = script_dir + "/resources/" + arg + ".properties"

                        if not os.path.isfile(lfile) or not os.access(lfile, os.R_OK):
                                print("Language file " + lfile + " doesn't exist or isn't readable")
                                sys.exit(2)
                        lang = arg
                elif opt in ("-o", "--output"):
                        ofile = arg
                elif opt in ("-p", "--passsthru"):
                        # read input from stdin, no outfile
                        ofile = None
                        source = ""
                        for line in sys.stdin:
                                source += line
                        # print "Source: " + source
                elif opt in ("-r", "--rawpasssthru"):
                        # read input from stdin, no outfile
                        rawpassthru = True
                        ofile = None
                        source = ""
                        for line in sys.stdin:
                                source += line

        if source is None:
                print("You have to provide a source file (-i option)")
                sys.exit(2)

        if rawpassthru:
                # parse raw ascii data
                result = ""
                keyboard = DuckEncoder.readResource(script_dir + "/resources/keyboard.properties")
                language = DuckEncoder.readResource(script_dir + "/resources/" + lang + ".properties")
                for line in source:
                        for c in line:
                                keydata = DuckEncoder.ASCIIChar2USBBytes(c, keyboard, language)
                                if len(keydata) > 0:
                                        result += keydata
        else:
                # parse source as DuckyScript
                result = DuckEncoder.generatePayload(source, lang)

        if ofile is None:
                # print to stdout
                # print(result)
                sys.stdout.write(result)
        else:
                # write to ofile
                with open(ofile, "wb") as f:
                        f.write(result)


if __name__ == "__main__":
        if len(sys.argv) < 2:
                usage()
                sys.exit()
        main(sys.argv[1:])
