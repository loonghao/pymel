"""
Functions for creating UI elements, as well as their class counterparts.
"""

import re, sys, functools, traceback

import pymel.util as _util
import pymel.internal.pmcmds as cmds
import pymel.internal.factories as _factories
import pymel.internal as _internal
import pymel.versions as _versions
from pymel.util import decorator

from language import mel, melGlobals
from system import Path as _Path
from contextlib import contextmanager
# Don't import uitypes  - we want to finish setting up the commands in this
# module before creating the uitypes classes; this way, the methods on the
# uitypes classes can use the functions from THIS module, and inherit things
# like simpleCommandWraps, etc
#import uitypes as _uitypes
    
_logger = _internal.getLogger(__name__)

_thisModule = sys.modules[__name__]
# Note - don't do
#     __import__('pymel.core.windows').XXX
# ...as this will get the 'original' module, not the dynamic one!
# Do:
#    import pymel.core.windows; import sys; sys.modules[pymel.core.windows].XXX
# instead!
thisModuleCmd = "import %s; import sys; sys.modules[%r]" % (__name__, __name__)

#-----------------------------------------------
#  Enhanced UI Commands
#-----------------------------------------------

def _lsUI( **kwargs ):
    long = kwargs.pop( 'long', kwargs.pop( 'l', True ) )
    head = kwargs.pop( 'head', kwargs.pop( 'hd', None ) )
    tail = kwargs.pop( 'tail', kwargs.pop( 'tl', None) )

    if not kwargs:
        kwargs = {
            'windows': 1, 'panels' : 1, 'editors' : 1, 'controls' : 1, 'controlLayouts' : 1,
            'collection' : 1, 'radioMenuItemCollections' : 1, 'menus' : 1, 'menuItems' : 1,
            'contexts' : 0, 'cmdTemplates' : 1
            }
    kwargs['long'] = long
    if head is not None: kwargs['head'] = head
    if tail is not None: kwargs['tail'] = tail
    return _util.listForNone(cmds.lsUI(**kwargs))

# all optionMenus are popupMenus, but not all popupMenus are optionMenus
_commandsToUITypes = {
    'optionMenu':'popupMenu',
    }

def _findLongName(name, type=None):
    # this remap is currently for OptionMenu, but the fix only works in 2011
    # lsUI won't list popupMenus or optionMenus
    kwargs = { 'long' : True}
    if type:
        kwargs['type'] = _commandsToUITypes.get(type, type)

    uiObjs = _util.listForNone(_lsUI( **kwargs ))
    res = [ x for x in uiObjs if x.endswith( '|' + name) ]
    if len(res) > 1:
        raise ValueError, "found more than one UI element matching the name %s" % name
    elif len(res) == 0:
        raise ValueError, "could not find a UI element matching the name %s" % name
    return res[0]

def lsUI( **kwargs ):
    """
Modified:
  - long defaults to True
  - if no type is passed, defaults to all known types
    """
    
    return [ _uitypes.PyUI(x) for x in _lsUI( **kwargs ) ]

scriptTableCmds = {}

def scriptTable(*args, **kwargs):
    """
Maya Bug Fix:
    - fixed getCellCmd to work with python functions, previously only worked with mel callbacks
        IMPORTANT: you cannot use the print statement within the getCellCmd callback function or your values will not be returned to the table
    """
        
    cb = kwargs.pop('getCellCmd', kwargs.pop('gcc',None) )
    cc = kwargs.pop('cellChangedCmd', kwargs.pop('ccc',None) )

    uiName = cmds.scriptTable( *args, **kwargs )
    if "q" in kwargs or "query" in kwargs:
        return uiName

    kwargs.clear()
    if cb:
        if hasattr(cb, '__call__'):
            procName = 'getCellMel%d' % len(scriptTableCmds.keys())
            key = '%s_%s' % (uiName,procName)

            procCmd = """global proc string %s( int $row, int $column ) {
                            return python(%s.scriptTableCmds['%s'](" + $row + "," + $column + ")");}
                      """ %  (procName, thisModuleCmd, key)
            mel.eval( procCmd )
            scriptTableCmds[key] = cb

            # create a scriptJob to clean up the dictionary of functions
            cmds.scriptJob(uiDeleted=(uiName, lambda *x: scriptTableCmds.pop(key,None)))
            cb = procName
        kwargs['getCellCmd'] = cb
    if cc:
        if hasattr(cc, '__call__'):
            procName = 'cellChangedCmd%d' % len(scriptTableCmds.keys())
            key = '%s_%s' % (uiName,procName)
            # Note - don't do
            #     __import__('pymel.core.windows').XXX
            # ...as this will get the 'original' module, not the dynamic one!
            # Do:
            #    import pymel.core.windows; import sys; sys.modules[pymel.core.windows].XXX
            # instead!
            procCmd = """global proc int %s( int $row, int $column, string $val) {
                            return python("%s.scriptTableCmds['%s'](" + $row + "," + $column + ",'" + $val + "')");}
                      """ %  (procName, thisModuleCmd, key)
            mel.eval( procCmd )
            scriptTableCmds[key] = cc

            # create a scriptJob to clean up the dictionary of functions
            cmds.scriptJob(uiDeleted=(uiName, lambda *x: scriptTableCmds.pop(key,None)))
            cc = procName
        kwargs['cellChangedCmd'] = cc

    if kwargs:
        cmds.scriptTable( uiName, e=1, **kwargs)
    return _uitypes.ScriptTable(uiName)

def getPanel(*args, **kwargs):
    typeOf = kwargs.pop('typeOf', kwargs.pop('to', None) )
    if typeOf:
        # typeOf flag only allows short names
        kwargs['typeOf'] = typeOf.rsplit('|',1)[-1]
    return cmds.getPanel(*args, **kwargs )
#
#
#def textScrollList( *args, **kwargs ):
#    """
#Modifications:
#  - returns an empty list when the result is None for queries: selectIndexedItem, allItems, selectItem queries
#    """
#    res = cmds.textScrollList(*args, **kwargs)
#    return _factories.listForNoneQuery( res, kwargs, [('selectIndexedItem', 'sii'), ('allItems', 'ai'), ('selectItem', 'si',)] )
#
#def optionMenu( *args, **kwargs ):
#    """
#Modifications:
#  - returns an empty list when the result is None for queries: itemListLong, itemListShort queries
#    """
#    res = cmds.optionMenu(*args, **kwargs)
#    return _factories.listForNoneQuery( res, kwargs, [('itemListLong', 'ill'), ('itemListShort', 'ils')] )
#
#def optionMenuGrp( *args, **kwargs ):
#    """
#Modifications:
#  - returns an empty list when the result is None for queries: itemlistLong, itemListShort queries
#    """
#    res = cmds.optionMenuGrp(*args, **kwargs)
#    return _factories.listForNoneQuery( res, kwargs, [('itemListLong', 'ill'), ('itemListShort', 'ils')] )
#
#def modelEditor( *args, **kwargs ):
#    """
#Modifications:
#  - casts to PyNode for queries: camera
#    """
#    res = cmds.modelEditor(*args, **kwargs)
#    if kwargs.get('query', kwargs.get('q')) and kwargs.get( 'camera', kwargs.get('cam')):
#        import general
#        return general.PyNode(res)
#    return res

#===============================================================================
# Provides classes and functions to facilitate UI creation in Maya
#===============================================================================

class BaseCallback(object):
    """
    Base class for callbacks.
    """
    def __init__(self,func,*args,**kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        #self.traceback = traceback.format_stack()    - we don't need tracebacks unless there's an exception

if _versions.current() >= _versions.v2009:

    class Callback(BaseCallback):
        """
        Enables deferred function evaluation with 'baked' arguments.
        Useful where lambdas won't work...

        It also ensures that the entire callback will be be represented by one
        undo entry.

        Example:

        .. python::

            import pymel as pm
            def addRigger(rigger, **kwargs):
                print "adding rigger", rigger

            for rigger in riggers:
                pm.menuItem(
                    label = "Add " + str(rigger),
                    c = Callback(addRigger,rigger,p=1))   # will run: addRigger(rigger,p=1)
        """
        def __call__(self,*args):
            cmds.undoInfo(openChunk=1)
            try:
                try:
                    return self.func(*self.args, **self.kwargs)
                except:
                    # not sure what CallbackError is for - it make the traceback unclear
                    #raise _factories.CallbackError(self, e)    
                    
                    # this method tweaks the traceback so that it 'skips' the callback object
                    t,v,tb = sys.exc_info()
                    raise t,v,tb.tb_next                    
            finally:
                cmds.undoInfo(closeChunk=1)

    class CallbackWithArgs(Callback):
        def __call__(self,*args,**kwargs):
            # not sure when kwargs would get passed to __call__,
            # but best not to remove support now
            kwargsFinal = self.kwargs.copy()
            kwargsFinal.update(kwargs)
            cmds.undoInfo(openChunk=1)
            try:
                try:
                    return self.func(*self.args + args, **kwargsFinal)
                except:
                    # this method tweaks the traceback so that it 'skips' the callback object
                    t,v,tb = sys.exc_info()
                    raise t,v,tb.tb_next                    
            finally:
                cmds.undoInfo(closeChunk=1)
else:

    class Callback(BaseCallback):
        """
        Enables deferred function evaluation with 'baked' arguments.
        Useful where lambdas won't work...
        Example:

        .. python::

            import pymel as pm
            def addRigger(rigger, **kwargs):
                print "adding rigger", rigger

            for rigger in riggers:
                pm.menuItem(
                    label = "Add " + str(rigger),
                    c = Callback(addRigger,rigger,p=1))   # will run: addRigger(rigger,p=1)
        """

        # This implementation of the Callback object uses private members
        # to store static call information so that the call can be made through
        # a mel call, thus making the entire function call undoable
        _callData = None
        @staticmethod
        def _doCall():
            (func, args, kwargs) = Callback._callData
            Callback._tb = None
            try:
                Callback._callData = func(*args, **kwargs)
            except:
                Callback._tb = sys.exc_info()
    
        def __call__(self,*args):
            Callback._callData = (self.func, self.args, self.kwargs)
            mel.python("%s.Callback._doCall()" % thisModuleCmd)
            if self._tb:
                t,v,tb = self._tb
                raise t,v,tb.tb_next
            return Callback._callData

    class CallbackWithArgs(Callback):
        def __call__(self,*args,**kwargs):
            kwargsFinal = self.kwargs.copy()
            kwargsFinal.update(kwargs)
            Callback._callData = (self.func, self.args + args, kwargsFinal)
            mel.python("%s.Callback._doCall()" % thisModuleCmd)
            if self._tb:
                t,v,tb = self._tb
                raise t,v,tb.tb_next
            return Callback._callData


def verticalLayout(*args, **kwargs):
    kwargs['orientation'] = 'vertical'
    return autoLayout(*args, **kwargs)

def horizontalLayout(*args, **kwargs):
    kwargs['orientation'] = 'horizontal'
    return autoLayout(*args, **kwargs)

def promptBox(title, message, okText, cancelText, **kwargs):
    """ Prompt for a value. Returns the string value or None if cancelled """
    ret = promptDialog(t=title, m=message, b=[okText,cancelText], db=okText, cb=cancelText,**kwargs)
    if ret==okText:
        return promptDialog(q=1,tx=1)

def promptBoxGenerator(*args, **kwargs):
    """ Keep prompting for values until cancelled """
    while 1:
        ret = promptBox(*args, **kwargs)
        if not ret: return
        yield ret

def confirmBox(title, message, yes="Yes", no="No", *moreButtons, **kwargs):
    """ Prompt for confirmation. Returns True/False, unless 'moreButtons' were specified, and then returns the button pressed"""

    default = kwargs.get("db", kwargs.get("defaultButton")) or yes

    ret = confirmDialog(t=title,    m=message,     b=[yes,no] + list(moreButtons),
                           db=default,
                           ma="center", cb=no, ds=no)
    if moreButtons:
        return ret
    else:
        return (ret==yes)

def informBox(title, message, ok="Ok"):
    """ Information box """
    confirmDialog(t=title, m=message, b=["Ok"], db="Ok")


class PopupError( Exception ):
    """Raise this exception in your scripts to cause a promptDialog to be opened displaying the error message.
    After the user presses 'OK', the exception will be raised as normal. In batch mode the promptDialog is not opened."""

    def __init__(self, msg):
        Exception.__init__(self, msg)
        if not cmds.about(batch=1):
            ret = informBox('Error', msg)


def promptForFolder(title='Select Folder', root=None, actionName='Select'):
    """ Prompt the user for a folder path """
    kw = {}
    if root:
        kw['dir'] = root

    folder = cmds.fileDialog2(cap=title, fm=3, okc=actionName, **kw)
    if not folder:
        return
    folder = _Path(folder[0])
    if folder.exists():
        return folder


def promptForPath(**kwargs):
    """ Prompt the user for a folder path """

    if cmds.about(linux=1):
        return _Path(fileDialog(**kwargs))

    else:
        # a little trick that allows us to change the top-level 'folder' variable from
        # the nested function ('getfolder') - use a single-element list, and change its content

        folder = [None]
        def getfolder(*args):
            folder[0] = args[0]

        kwargs.pop('fileCommand',None)
        kwargs['fc'] = getfolder

        kwargs['an'] = kwargs.pop('an', kwargs.pop('actionName', "Select File"))
        ret = cmds.fileBrowserDialog(**kwargs)
        folder = _Path(folder[0])
        if folder.exists():
            return folder


def fileDialog(*args, **kwargs):
    ret = cmds.fileDialog(*args, **kwargs )
    if ret:
        return _Path( ret )

@contextmanager
def hourglassShown():
    """
    Create a context where the hourglass is shown.
    
    Example:
    
        with hourglassShown():
            for i in xrange(10):
                print i
    """
    cmds.waitCursor(st=True)
    try:
        yield
    finally:
        cmds.waitCursor(st=False)
    

@decorator
def showsHourglass(func):
    """ Decorator - shows the hourglass cursor until the function returns """
    def decoratedFunc(*args, **kwargs):
        with hourglassShown():
            return func(*args, **kwargs)
    return decoratedFunc

_lastException = None
def announcesExceptions(title="Exception Caught", message="'%(exc)s'\nCheck script-editor for details", ignoredExecptiones=None):
    """
    Decorator - shows an information box to the user with any exception raised in a sub-routine.
    Note - the exception is re-raised.
    
    @param title: The title of the message-box
    @param message: The message in the message box, string-formatted with 'exc' as the exception object 

    """
    
    if not ignoredExecptiones:
        ignoredExecptiones = tuple()
    else:
        ignoredExecptiones = tuple(ignoredExecptiones)
    if callable(title):
        func = title
        title = "Exception Caught"
    else:
        func = None
    
    @decorator
    def decoratingFunc(func):
        def decoratedFunc(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ignoredExecptiones:
                raise
            except Exception, e:
                global _lastException
                if e is _lastException:
                    return
                else:
                    _lastException = e
                from maya.utils import executeDeferred 
                executeDeferred(informBox, title, message % dict(exc=e))
                raise
        return decoratedFunc
    if func:
        return decoratingFunc(func)
    return decoratingFunc


def pathButtonGrp( name=None, *args, **kwargs ):
        
    if name is None or not cmds.textFieldButtonGrp( name, ex=1 ):
        create = True
    else:
        create = False

    return _uitypes.PathButtonGrp( name=name, create=create, *args, **kwargs )

def folderButtonGrp( name=None, *args, **kwargs ):
        
    if name is None or not cmds.textFieldButtonGrp( name, ex=1 ):
        create = True
    else:
        create = False

    return _uitypes.FolderButtonGrp( name=name, create=create, *args, **kwargs )

def vectorFieldGrp( *args, **kwargs ):
    
    return _uitypes.VectorFieldGrp( *args, **kwargs )


def uiTemplate(name=None, force=False, exists=None):
        
    if exists:
        return cmds.uiTemplate(name, exists=1)
    else:
        return _uitypes.UITemplate(name=name, force=force)

def setParent(*args, **kwargs):
    """
Modifications
  - returns None object instead of the string 'NONE'
    """
        
    result = cmds.setParent(*args, **kwargs)
    if kwargs.get('query', False) or kwargs.get('q', False):
        if result == 'NONE':
            result = None
        else:
            result = _uitypes.PyUI(result)
    return result

def currentParent():
    "shortcut for ``ui.PyUI(setParent(q=1))`` "
    
    return setParent(q=1)

def currentMenuParent():
    "shortcut for ``ui.PyUI(setParent(q=1, menu=1))`` "
    return setParent(q=1, menu=1)

def textLayout(text, parent=None):
    return _uitypes.TextLayout(text=text, parent=parent, create=True)

def objectMenu(*args, **kwargs):
    kwargs['create']=True
    return _uitypes.ObjectMenu(*args, **kwargs)

def objectScrollList(*args, **kwargs):
    kwargs['create']=True
    return _uitypes.ObjectScrollList(*args, **kwargs)

def objectTreeView(*args, **kwargs):
    kwargs['create']=True
    return _uitypes.ObjectTreeView(*args, **kwargs)

def textWindow(title, text, size=(300,300)):
    """
    Convenience for creating a simple window with a scroll-field of text inside

    @param title: The window title
    @param text: The text to display 
    @param size: A tuple of (xdim,ydim) to size the window
    
    """

    self = window("TextWindow#",title=title)
    self.main = textLayout(parent=self, text=text)
    self.setWidthHeight(list(size or [300,300]))
    self.setText = self.main.setText
    self.show()
    return self

def labeledControl(label, uiFunc, kwargs, align="left", parent=None, ratios=None):
    """
    A convenience for getting a label and a control (specified by uiFunc+kwargs),
    in an adjustable horizontal layout.
    It is also more controllable and aesthetically pleasing than the *Grp controls 
    (textFieldGrp, optionMenuGrp, intFieldGrp, etc.)
    
    @param uiFunc: The function used to create the desired control
    @param kwargs: keyword arguments, as a dictionary, to be passed to the uiFunc
    @param align: how to align the text in the label ("left" or "right")
    @param parent: The parent layout for this group of ui elements
    @param ratios: the distribution of space for the label and the control. See 'FormLayout' 
    
    Example:
        # create an optionMenu with no label of its own (l=""), and a separate "Options:" text element.
        # The label will occupy the least space necessary, and the optionMenu will auto-adjust its size (ratios=[0,1]) 
        labeledControl(label="Options:", uiFunc=pm.optionMenu, kwargs=dict(l=""), ratios=[0,1])
    """
    kw = dict(ratios=ratios)
    if parent:
        kw['parent']=parent
    with horizontalLayout(**kw) as layout:
        label = text(l=label,al=align)
        control = uiFunc(**kwargs)
            
    if not isinstance(control,_uitypes.PyUI):
        control = _uitypes.PyUI(control)
    control.label = label 
    control.layout = layout
    return control        

# fix a bug it becomes impossible to create a menu after setParent has been called
def menu(*args, **kwargs):
    """
Modifications
  - added ability to query parent
    """
    if _versions.current() < _versions.v2011:
        # on create only
        if not ( kwargs.get('query', False) or kwargs.get('q', False) ) \
            and not ( kwargs.get('edit', False) or kwargs.get('e', False) ) \
            and not ( kwargs.get('parent', False) or kwargs.get('p', False) ):
            kwargs['parent'] = cmds.setParent(q=1)

    if ( kwargs.get('query', False) or kwargs.get('q', False) ) \
            and ( kwargs.get('parent', False) or kwargs.get('p', False) ):
        name = unicode(args[0])
        if '|' not in name:
            try:
                name = _findLongName(name, 'menu')
            except ValueError:
                name = _findLongName(name, 'popupMenu')
        return name.rsplit('|',1)[0]

    result = cmds.menu(*args, **kwargs)

    if ( kwargs.get('query', False) or kwargs.get('q', False) ) \
            and ( kwargs.get('itemArray', False) or kwargs.get('ia', False) ) \
            and result is None:
        result = []
    return result

def _createClassCommands():
    def createCallback( classname ):
        """
        create a callback that will trigger lazyLoading
        """
        def callback(*args, **kwargs):
            
            res = getattr(_uitypes, classname)(*args, **kwargs)
            return res
        return callback

    for funcName in _factories.uiClassList:
        # Create Class
        classname = _util.capitalize(funcName)
        #cls = _uitypes[classname]

        # Create Function
        func = _factories.functionFactory( funcName, createCallback(classname), _thisModule, uiWidget=True )
        if func:
            func.__module__ = __name__
            setattr(_thisModule, funcName, func)


def _createOtherCommands():
    moduleShortName = __name__.split('.')[-1]
    nonClassFuncs = set(_factories.moduleCmds[moduleShortName]).difference(_factories.uiClassList)
    for funcName in nonClassFuncs:
        func = _factories.functionFactory( funcName, returnFunc=None, module=_thisModule )
        if func:
            func.__module__ = __name__
            setattr(_thisModule, funcName, func)
            # want this call to work regardless of order we call _createClassCommandParis / _createCommands
            if sys.modules[__name__] != _thisModule:
                setattr( sys.modules[__name__], funcName, func )

_createClassCommands()
_createOtherCommands()

def autoLayout(*args, **kwargs):
    
    return _uitypes.AutoLayout(*args, **kwargs)

autoLayout.__doc__ = formLayout.__doc__

def subMenuItem(*args, **kwargs):
    """
    shortcut for ``menuItem(subMenu=True)``
    """
    kwargs['subMenu'] = True
    return menuItem(*args, **kwargs)



#class ValueControlGrp( UI ):
#    def __new__(cls, name=None, create=False, dataType=None, numberOfControls=1, **kwargs):
#
#        if cls._isBeingCreated(name, create, kwargs):
#            assert dataType
#            if not isinstance(dataType, basestring):
#                try:
#                    dataType = dataType.__name__
#                except AttributeError:
#                    dataType = str(dataType)
#
#            # if a dataType such as float3 or int2 was passed, get the number of ctrls
#            try:
#                numberOfControls = int(re.search( '(\d+)$', dataType ).group(0))
#            except:
#                pass
#
#            dataType = dataType.lower()
#
#            kwargs.pop('dt',None)
#            kwargs['docTag'] = dataType
##            kwargs.pop('nf', None)
##            kwargs['numberOfFields'] = 3
##            name = cmds.floatFieldGrp( name, *args, **kwargs)
#
#        #labelStr = kwargs.pop( 'label', kwargs.pop('l', str(dataType) ) )
#        if dataType in ["bool"]:
#            ctrl = _uitypes.CheckBoxGrp
#            getter = ctrl.getValue1
#            setter = ctrl.setValue1
#            #if hasDefault: ctrl.setValue1( int(default) )
#
#        elif dataType in ["int"]:
#            ctrl = _uitypes.IntFieldGrp
#            getter = ctrl.getValue1
#            setter = ctrl.setValue1
#            #if hasDefault: ctrl.setValue1( int(default) )
#
#        elif dataType in ["float"]:
#            ctrl = _uitypes.FloatFieldGrp
#            getter = ctrl.getValue1
#            setter = ctrl.setValue1
#            #if hasDefault: ctrl.setValue1( float(default) )
#
#        elif dataType in ["vector", "Vector"]:
#            ctrl = VectorFieldGrp
#            getter = ctrl.getVector
#            setter = ctrl.setValue1
#            #if hasDefault: ctrl.setVector( default )
#
#        elif dataType in ["path", "Path", "FileReference"]:# or pathreg.search( argName.lower() ):
#            ctrl = PathButtonGrp
#            getter = ctrl.getPath
#            setter = ctrl.setPath
#            #if hasDefault: ctrl.setText( default.__repr__() )
#
#        elif dataType in ["string", "unicode", "str"]:
#            ctrl = _uitypes.TextFieldGrp
#            getter = ctrl.getText
#            setter = ctrl.setText
#            #if hasDefault: ctrl.setText( str(default) )
#        else:
#             raise TypeError
##        else:
##            ctrl = _uitypes.TextFieldGrp( l=labelStr )
##            getter = makeEvalGetter( ctrl.getText )
##            #setter = ctrl.setValue1
##            #if hasDefault: ctrl.setText( default.__repr__() )
#        cls.__melcmd__ = staticmethod( ctrl.__melcmd__ )
#        self = ctrl.__new__( cls, name, create, **kwargs )
#        self.getter = getter
#        self.ctrlClass = ctrl
#        return self
#
#    def getValue(self):
#        return self.getter(self)

def valueControlGrp(name=None, create=False, dataType=None, slider=True, value=None, numberOfControls=1, **kwargs):
    """
    This function allows for a simplified interface for automatically creating UI's to control numeric values.

    A dictionary of keywords shared by all controls can be created and passed to this function and settings which don't pertain
    to the element being created will will be ignore.  For example, 'precision' will be ignored by all non-float UI and
    'sliderSteps' will be ignore by all non-slider UIs.

    :Parameters:
        dataType : string or class type
            The dataType that the UI should control.  It can be a type object or the string name of the type.
            For example for a boolean, you can specify 'bool' or pass in the bool class. Also, if the UI is meant to
            control an array, you can pass the type name as a stirng with a integer suffix representing the array length. ex. 'bool3'

        numberOfControls : int
            A parameter for specifying the number of controls per control group.  For example, for a checkBoxGrp, numberOfControls
            will map to the 'numberOfCheckBoxes' keyword.

        slider : bool
            Specify whether or not sliders should be used for int and float controls. Ignored for other
            types, as well as for int and float arrays

        value : int, int list, bool, bool list, float, float list, string, unicode, Path, Vector,
            The value for the control. If the value is for an array type, it should be a list or tuple of the appropriate
            number of elements.

    A straightforward example:

    .. python::

        settings = {}
        settings['step'] = 1
        settings['precision'] = 3
        settings['vertical'] = True # for all checkBoxGrps, lay out vertically
        win = window()
        columnLayout()
        setUITemplate( 'attributeEditorTemplate', pushTemplate=1 )
        boolCtr = valueControlGrp( dataType='bool', label='bool', **settings)
        bool3Ctr = valueControlGrp( dataType='bool', label='bool', numberOfControls=3, **settings)
        intCtr = valueControlGrp( dataType=int, label='int', slider=False, **settings)
        intSldr = valueControlGrp( dataType=int, label='int', slider=True, **settings)
        int3Ctrl= valueControlGrp( dataType=int, label='int', numberOfControls=3, **settings)
        floatCtr = valueControlGrp( dataType=float, label='float', slider=False, **settings)
        floatSldr = valueControlGrp( dataType=float, label='float', slider=True, **settings)
        pathCtrl = valueControlGrp( dataType=Path, label='path', **settings)
        win.show()


    Here's an example of how this is meant to be used in practice:

    .. python::

        settings = {}
        settings['step'] = 1
        settings['precision'] = 3
        win = window()
        columnLayout()
        types=[ ( 'donuts?',
                    bool,
                    True ),
                # bool arrays have a special label syntax that allow them to pass sub-labels
                ( [ 'flavors', ['jelly', 'sprinkles', 'glazed']],
                    'bool3',
                    [0,1,0]),
                ( 'quantity',
                  int,
                  12 ),
                ( 'delivery time',
                  float,
                  .69)
                ]
        for label, dt, val in types:
            valueControlGrp( dataType=dt, label=label, value=val, **settings)
        win.show()

    """
    

    def makeGetter( ctrl, methodName, num ):
        def getter( ):
            res = []
            for i in range( num ):
                res.append( getattr(ctrl, methodName + str(i+1) )() )
            return res
        return getter

    def makeSetter( ctrl, methodName, num ):
        def setter( args ):
            for i in range( num ):
                getattr(ctrl, methodName + str(i+1) )(args[i])
        return setter

    # the options below are only valid for certain control types.  they can always be passed to valueControlGrp, but
    # they will be ignore if not applicable to the control for this dataType.  this allows you to create a
    # preset configuration and pass it to the valueControlGrp for every dataType -- no need for creating switches, afterall
    # that's the point of this function

    sliderArgs = [ 'sliderSteps', 'ss', 'dragCommand', 'dc' ]
    fieldArgs = [ 'field', 'f', 'fieldStep', 'fs', 'fieldMinValue', 'fmn', 'fieldMaxValue', 'fmx' ]
    fieldSliderArgs = ['step', 's', 'minValue', 'min', 'maxValue', 'max', 'extraLabel', 'el'] + sliderArgs + fieldArgs
    floatFieldArgs = ['precision', 'pre']
    verticalArgs = ['vertical', 'vr'] #checkBoxGrp and radioButtonGrp only

    if _uitypes.PyUI._isBeingCreated(name, create, kwargs):
        assert dataType, "You must pass a dataType when creating a new control"
        if not isinstance(dataType, basestring):
            try:
                dataType = dataType.__name__
            except AttributeError:
                dataType = str(dataType)

        # if a dataType such as float3 or int2 was passed, get the number of ctrls
        try:
            buf = re.split( '(\d+)', dataType )
            dataType = buf[0]
            numberOfControls = int(buf[1])
        except:
            pass
    else:
        # control command lets us get basic info even when we don't know the ui type
        dataType = control( name, q=1, docTag=1)
        assert dataType

    numberOfControls = int(numberOfControls)
    if numberOfControls < 1:
        numberOfControls = 1
    elif numberOfControls > 4:
        numberOfControls = 4

    #dataType = dataType.lower()
    kwargs.pop('dt',None)
    kwargs['docTag'] = dataType

    if dataType in ["bool"]:
        if numberOfControls > 1:
            kwargs.pop('ncb', None)
            kwargs['numberOfCheckBoxes'] = numberOfControls

        # remove field/slider and float kwargs
        for arg in fieldSliderArgs + floatFieldArgs:
            kwargs.pop(arg, None)

        # special label handling
        label = kwargs.get('label', kwargs.get('l',None) )
        if label is not None:
            # allow label passing with additional sub-labels:
            #    ['mainLabel', ['subLabel1', 'subLabel2', 'subLabel3']]
            if _util.isIterable(label):
                label, labelArray = label
                kwargs.pop('l',None)
                kwargs['label'] = label
                kwargs['labelArray' + str(numberOfControls) ] = labelArray

        ctrl = _uitypes.CheckBoxGrp( name, create, **kwargs )

        if numberOfControls > 1:
            getter = makeGetter(ctrl, 'getValue', numberOfControls)
            setter = makeSetter(ctrl, 'setValue', numberOfControls)
        else:
            getter = ctrl.getValue1
            setter = ctrl.setValue1
        #if hasDefault: ctrl.setValue1( int(default) )

    elif dataType in ["int"]:
        if numberOfControls > 1:
            kwargs.pop('nf', None)
            kwargs['numberOfFields'] = numberOfControls
            slider = False

        if slider:
            # remove float kwargs
            for arg in floatFieldArgs + verticalArgs:
                kwargs.pop(arg, None)
            # turn the field on by default
            if 'field' not in kwargs and 'f' not in kwargs:
                kwargs['field'] = True

            ctrl = _uitypes.IntSliderGrp( name, create, **kwargs )
            getter = ctrl.getValue
            setter = ctrl.setValue
        else:
            # remove field/slider and float kwargs
            for arg in fieldSliderArgs + floatFieldArgs + verticalArgs:
                kwargs.pop(arg, None)
            ctrl = _uitypes.IntFieldGrp( name, create, **kwargs )

            getter = ctrl.getValue1
            setter = ctrl.setValue1
        #if hasDefault: ctrl.setValue1( int(default) )

    elif dataType in ["float"]:
        if numberOfControls > 1:
            kwargs.pop('nf', None)
            kwargs['numberOfFields'] = numberOfControls
            slider = False

        if slider:
            for arg in verticalArgs:
                kwargs.pop(arg, None)

            # turn the field on by default
            if 'field' not in kwargs and 'f' not in kwargs:
                kwargs['field'] = True
            ctrl = _uitypes.FloatSliderGrp( name, create, **kwargs )
            getter = ctrl.getValue
            setter = ctrl.setValue
        else:
            # remove field/slider kwargs
            for arg in fieldSliderArgs + verticalArgs:
                kwargs.pop(arg, None)
            ctrl = _uitypes.FloatFieldGrp( name, create, **kwargs )
            getter = ctrl.getValue1
            setter = ctrl.setValue1
        #if hasDefault: ctrl.setValue1( float(default) )

    elif dataType in ["vector", "Vector"]:
        # remove field/slider kwargs
        for arg in fieldSliderArgs + floatFieldArgs + verticalArgs:
            kwargs.pop(arg, None)
        ctrl = VectorFieldGrp( name, create, **kwargs )
        getter = ctrl.getVector
        setter = ctrl.setValue1
        #if hasDefault: ctrl.setVector( default )

    elif dataType in ["path", "Path", "FileReference"]:# or pathreg.search( argName.lower() ):
        # remove field/slider kwargs
        for arg in fieldSliderArgs + floatFieldArgs + verticalArgs:
            kwargs.pop(arg, None)
        ctrl = PathButtonGrp( name, create, **kwargs )
        getter = ctrl.getPath
        setter = ctrl.setPath
        #if hasDefault: ctrl.setText( default.__repr__() )

    elif dataType in ["string", "unicode", "str"]:
        # remove field/slider kwargs
        for arg in fieldSliderArgs + floatFieldArgs + verticalArgs:
            kwargs.pop(arg, None)
        ctrl = _uitypes.TextFieldGrp( name, create, **kwargs )
        getter = ctrl.getText
        setter = ctrl.setText
        #if hasDefault: ctrl.setText( str(default) )
    else:
        raise TypeError, "Unsupported dataType: %s" % dataType
#        else:
#            ctrl = _uitypes.TextFieldGrp( l=labelStr )
#            getter = makeEvalGetter( ctrl.getText )
#            #setter = ctrl.setValue1
#            #if hasDefault: ctrl.setText( default.__repr__() )

        #new = ctrl( name, create, **kwargs )
    ctrl.getValue = getter
    ctrl.setValue = setter
    ctrl.dataType = ctrl.getDocTag

    if value is not None:
        ctrl.setValue(value)

    # TODO : remove setDocTag
    return ctrl


def getMainProgressBar():
    return _uitypes.ProgressBar(melGlobals['gMainProgressBar'])


@contextmanager
def progressShown(estimatedSteps=None, title=None, id=None):
    """
    Shows an interruptible progress window that is driven by log messages issued in the 
    current context (using python's built-in logging module).
    
    
    @param estimatedSteps: Will be used to set the range of the progress bar for this context
    @param title: Sets the title of the progress window
    @param id: Used to uniquely identify the current context for caching estimated steps  
    
    See uitype.ProgressWindow for more info.
    See showsProgress for a decorator variant of this function
    
    Example:
    
    import logging
    
    n = 10000
    with progressShown(estimatedSteps=n, title="Processing...") as progressWin:
        progressWin.status = "something's happening..."
        for i in xrange(n):
            logging.debug(i)                         # any log message will step up the progress
    
    func(10000)
    """

    pw = _uitypes.ProgressWindow()
    pw.processBegin(id, estimatedSteps, title)
    try:
        yield pw
    except pw.StoppedByUser, e:
        raise pw.StoppedByUser(str(e))
    finally:
        pw.processEnd()

@decorator
def showsProgress(func):
    """
    Decorator - makes the function show an interruptible progress window that is 
    driven by log messages (using python's built-in logging module).
    
    See uitype.ProgressWindow for more info.
    See progressShown for a context-manager variant of this function
    
    Example:
    
    import logging
    
    @showProgress
    def func(n):
        logging.info("something's happening...")     # INFO messages show in the progress window status
        for i in xrange(n):
            logging.debug(i)                         # any log message will step up the progress
    
    func(10000)
    """
    def progressingFunc(*args, **kwargs):
        with progressShown(id=func) as progressBar:
            return func(*args, **kwargs)
    return progressingFunc


# Now that we've actually created all the functions, it should be safe to import
# _uitypes...
if _versions.current() >= _versions.v2011:
    from uitypes import toQtObject, toQtLayout, toQtControl, toQtMenuItem, toQtWindow
import uitypes as _uitypes