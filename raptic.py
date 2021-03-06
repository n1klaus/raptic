#!/usr/bin/env python3
from dialog import Dialog
from subprocess import check_output, call, CalledProcessError, Popen, DEVNULL
from configparser import ConfigParser
from os.path import abspath, expanduser, expandvars, isfile
from time import sleep


class ConfigOption:
   def __init__(self, name, label, description, option_type, default, required=True):
      self.name = name
      self.label = label
      self.description = description
      self.option_type = option_type
      self.default = default
      self.required = required


class RAPTIC:
   configuration_options = {
         'Server': ConfigOption('server', 'Server',
            'Hostname or IP-Address of the ThinClient-Host-Server', str, '', True),
         'Username': ConfigOption('user', 'Username',
            'Username of the user that should be used by this ThinClient', str, '', True),
         'Fullscreen': ConfigOption('fullscreen', 'Fullscreen',
            'Run rdesktop in fullscreen mode (default: yes)', bool, 'yes', False),
      }

   def __init__(self):
      ''' Initialize RAPTIC. '''
      self.dialog = Dialog(dialog='dialog', autowidgetsize=True)
      self.dialog.set_background_title("RAPTIC - an easy thin client for raspberry pi")

      self.__read_config()

   def __read_config(self):
      '''
      Load the configuration for RAPTIC.

      There are multiple locations for the config file. They are used exclusively and are tested in
      the following order:
         - ~/.raptic
         - ~/.config/raptic
      '''
      self.__config_path = ''
      self.config = ConfigParser()
      for filename in ['~/.raptic', '~/.config/raptic']:
         filename = abspath(expanduser(expandvars(filename)))
         if isfile(filename):
            self.config.read(filename)
            self.__config_path = filename
            break
      if not self.__config_path:
         self.__config_path = abspath(expanduser(expandvars('~/.raptic')))

   def __first_start(self):
      ''' Show dialogs to configure RAPTIC on the first execution. '''
      self.dialog.msgbox(('Welcome to RAPTIC!\nThis appears to be the first time you run RAPTIC on '
         'this PC. We therefore will generate a new configuration in the following steps.'))

      self.config['general'] = {}
      for label, option in RAPTIC.configuration_options.items():
         if option.required:
            code, value = self.dialog.inputbox(option.label)
            if code != self.dialog.OK:
               self.dialog.msgbox('Configuration aborted. No configuration file written...')
         else:
            value = option.default
         self.config['general'][option.name] = value
      try:
         self.__config_save()
         self.dialog.msgbox('Configuration file has been written. You can now start using RAPTIC.')
      except FileNotFoundError:
         self.dialog.msgbox('Configuration file ({}) is not writeable.'.format(self.__config_path))
         self.exit(1)

   def __config_edit(self):
      ''' Show menu for editing the configuration. '''
      config_changed = False
      config_tmp = ConfigParser()
      config_tmp.update(self.config)
      while True:
         code, tag = self.dialog.menu('What setting do you want to change?',
               choices=[(option.label, config_tmp['general'][option.name]) for option in
                  RAPTIC.configuration_options.values()], ok_label='CHANGE', cancel_label='BACK',
               extra_button=True, extra_label='SAVE')

         if code == self.dialog.CANCEL:
            if config_changed:
               code_exit = self.dialog.yesno('Do you really want to go back without saving the configuration?')
               if code_exit == self.dialog.OK:
                  return
            else:
               return

         if code == self.dialog.OK:
            option = RAPTIC.configuration_options[tag]
            if option.option_type == bool:
               current_value = config_tmp.getboolean('general', option.name)
               code_change, value = self.dialog.radiolist(option.label, choices=[
                  ('yes', '', current_value),
                  ('no', '', not current_value)],
                  default_item='yes' if current_value else 'no')
            else:
               code_change, value = self.dialog.inputbox(option.label,
                     init=config_tmp['general'][option.name])
            if code_change == self.dialog.OK:
               config_changed = True
               config_tmp['general'][option.name] = value

         if code == self.dialog.EXTRA:
            self.config.update(config_tmp)
            try:
               self.__config_save()
               self.dialog.msgbox('The config has been written to file.', title='RAPTIC')
            except FileNotFoundError:
               self.dialog.msgbox('Configuration file ({}) is not writeable.'.format(
                  self.__config_path), title='ERROR')
            return

   def __config_save(self):
      ''' Save the configuration to file. '''
      with open(self.__config_path, 'w') as f:
         self.config.write(f)

   def __rdesktop_start(self):
      ''' Run `rdesktop` via `xinit`. '''
      try:
         rdesktop_path = check_output(['which', 'rdesktop']).decode('utf8').strip()
      except CalledProcessError:
         self.dialog.msgbox(('It appears that rdesktop is not in your PATH. This could be because'
            'of wrong settings or rdesktop is currently not installed.'))
         self.exit(1)

      command = 'xinit {rdesktop} -u {user} {server} {fullscreen}'.format(
            rdesktop=rdesktop_path,
            user = self.config.get('general', 'user'),
            server = self.config.get('general', 'server'),
            fullscreen = '-f' if self.config.getboolean('general', 'fullscreen') else ''
         )
      call(command, shell=True, stderr=DEVNULL, stdout=DEVNULL)

   def __desktop_environment_start(self):
      ''' Run desktop environment by calling `startx`. '''
      call('startx', shell=True)

   def __menu(self):
      ''' Show the main menu and call the selected action. '''
      code, tag = self.dialog.menu('What do you want to do?',
            choices=[
               ('1', 'Start ThinClient'),
               ('2', 'Change configuration'),
               ('3', 'Start desktop environment'),
               ('x', 'Exit RAPTIC')], nocancel=True)

      if code != self.dialog.OK:
         self.exit(1)

      if tag == '1':
         self.__rdesktop_start()
      elif tag == '2':
         self.__config_edit()
      elif tag == '3':
         self.__desktop_environment_start()
      elif tag == 'x':
         return False
      return True

   def run(self):
      ''' Start RAPTIC. '''
      if not self.config.sections():
         self.__first_start()

      while True:
         if not self.__menu():
            self.exit(0)

   def exit(self, code):
      ''' Clear the screen and exit the application with given status code. '''
      Popen('clear', shell=False, stdout=None, stderr=None, close_fds=True)
      exit(code)


if __name__ == '__main__':
   import locale
   locale.setlocale(locale.LC_ALL, '')
   raptic = RAPTIC()
   raptic.run()
