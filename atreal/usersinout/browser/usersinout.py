# -*- coding: utf-8 -*-

import csv
from StringIO import StringIO
import os

from zope.interface import implements
import transaction

from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from atreal.usersinout import UsersInOutMessageFactory as _
from atreal.usersinout.config import CSV_HEADER, MEMBER_PROPERTIES, VERSUS_CADASTRO, VERSUS_FORM_VIVENCIA
from unicodedata import normalize

from Products.VersusInscricoes.utils.util import GenericMethods
from Products.VersusInscricoes.utils.estados import LISTA_ESTADOS
from DateTime import DateTime
from datetime import datetime


class UsersInOut (BrowserView):
    """Users import and export as CSV files.
    """

    invalidLines = []

    def __call__(self):
        self.invalidLines = []
        method = self.request.get('REQUEST_METHOD', 'GET')
        self.catalog = getToolByName(self.context, 'portal_catalog')
        if (method != 'POST') or not int(self.request.form.get('form.submitted', 0)):
            return self.index()

        if self.request.form.get('form.button.Cancel'):
            return self.request.response.redirect('%s/plone_control_panel' \
                                                  % self.context.absolute_url())

        if self.request.form.get('form.button.Import'):
            return self.importUsers()

        if self.request.form.get('form.button.CSVErrors'):
            return self.getCSVWithErrors()

        if self.request.form.get('form.button.Export'):
            return self.exportUsers()

    def get_all_cop(self):
        """ Get all communities
        """
        items = []
        cops = self.catalog(portal_type='CoP')
        for cop in cops:
            items.append({'value':cop.UID, 'title':cop.Title})
        return items

    def insert_user_cop(self, cop_participants):
        from communities.practice.generics.generics import addParticipantsInBlock
        cop = self.request.form.get('community_insert',None)
        if cop:
            result = self.catalog(UID=cop)
            if result:
                cop = result[0].getObject()
                addParticipantsInBlock(cop, cop_participants)
                return True
        return False

    def getCSVTemplate(self):
        """Return a CSV template to use when importing members."""
        datafile = self._createCSV([])
        return self._createRequest(datafile.getvalue(), "users_sheet_template.csv")

    def importUsers(self):
        """Import users from CSV file.

        In case of error, return a CSV file filled with the lines where
        errors occured.
        """
        file_upload = self.request.form.get('csv_upload', None)
        if file_upload is None or not file_upload.filename:
            return

        # verify csv delimiter
        dialect = csv.Sniffer().sniff(file_upload.read(), delimiters=";,")
        file_upload.seek(0)

        reader = csv.reader(file_upload, dialect)
        header = reader.next()

        if header != CSV_HEADER:
            msg = _('Wrong specification of the CSV file. Please correct it and retry.')
            type = 'error'
            IStatusMessage(self.request).addStatusMessage(msg, type=type)
            return self.index()

        pr = getToolByName(self.context, 'portal_registration')
        pg = getToolByName(self.context, 'portal_groups')
        acl = getToolByName(self.context,'acl_users')
        pm = getToolByName(self.context, 'portal_membership')
        groupsIds = set([item['id'] for item in acl.searchGroups()])
        groupsDict = {}
        validLines = []
        cop_participants = []
        versus_participants = []

        groupsNumber = 0
        for line in reader:
            datas = dict(zip(header, line))
            try:
                groups = [g.strip() for g in datas.pop('groups').split(',') if g]
                for group in groups:
                    if not group in groupsIds: # New group, 'have to create it
                        pg.addGroup(group)
                        groupsNumber += 1

            except:
                self.invalidLines.append(line)
                print "Invalid line: %s" % line
                continue
            validLines.append(line)

        usersNumber = 0

        for line in validLines:
            datas = dict(zip(header, line))
            try:
                username = datas['username']

                # try to find user by cpf or email
                user = pm.searchForMembers(cpf=datas['cpf']) or pm.searchForMembers(email=datas['email'])
                if user:
                    username = user[0].getId()
                else:
                    # try to find user by id
                    user = pm.getMemberById(username)

                if not user:
                    groups = [g.strip() for g in datas.pop('groups').split(',') if g]
                    password = datas.pop('password')
                    if not password:
                        password = username.split('@')[0]

                    member_data = {key: value for (key, value) in datas.iteritems() if key in MEMBER_PROPERTIES}
                    roles = datas.pop('roles').split(',')
                    pr.addMember(username, password, roles, [], datas)
                    for group in groups:
                        if not group in groupsDict.keys():
                            groupsDict[group] = acl.getGroupById(group)
                        groupsDict[group].addMember(username)

                datas["username"] = username
                cop_participants.append(username)
                versus_participants.append(datas)
                usersNumber += 1
            except Exception, e:
                self.invalidLines.append(line)
                print "Invalid line: %s" % e

        self.insert_user_cop(cop_participants)
        self._insert_versus_participant(versus_participants)

        if self.invalidLines:
            datafile = self._createCSV(self.invalidLines)
            self.request['csverrors'] = True
            self.request.form['users_sheet_errors'] = datafile.getvalue()
            msg = _('Some errors occured. Please check your CSV syntax and retry.')
            type = 'error'
        else:
            msg, type = _('Members successfully imported.'), 'info'

        IStatusMessage(self.request).addStatusMessage(msg, type=type)
        self.request['users_results'] = usersNumber
        self.request['groups_results'] = groupsNumber
        return self.index()

    def getCSVWithErrors(self):
        """Return a CSV file that contains lines witch failed."""

        users_sheet_errors = self.request.form.get('users_sheet_errors', None)
        if users_sheet_errors is None:
            return # XXX
        return self._createRequest(users_sheet_errors, "users_sheet_errors.csv")

    def exportUsers(self):
        """Export users within CSV file."""
        self.pms = getToolByName(self.context,'portal_membership')
        pg = getToolByName(self.context,'portal_groups')
        acl = getToolByName(self.context,'acl_users')
        gids = set([item['id'] for item in acl.searchGroups()])
        self.group_roles = {}
        for gid in gids:
            self.group_roles[gid] = pg.getGroupById(gid).getRoles()
        datafile = self._createCSV(self._getUsersInfos())
        return self._createRequest(datafile.getvalue(), "users_sheet_export.csv")

    def _getUsersInfos(self):
        """Generator filled with the members data."""
        acl = getToolByName(self.context, 'acl_users')
        for user in acl.searchUsers():
            if not user['pluginid'] == 'mutable_properties':
                yield self._getUserData(user['userid'])

    def _getUserData(self,userId):
        member = self.pms.getMemberById(userId)
        groups = member.getGroups()
        group_roles = []
        for gid in groups:
            group_roles.extend(self.group_roles.get(gid, []))
        roles = [role for role in member.getRoles() if not role in group_roles]
        props = [userId, '', ','.join(roles)] # userid, password, roles
        if member is not None:
            for p in MEMBER_PROPERTIES:
                props.append(member.getProperty(p))
        props.append(','.join(groups)) # groups
        return props

    def _createCSV(self, lines):
        """Write header and lines within the CSV file."""
        datafile = StringIO()
        writor = csv.writer(datafile)
        writor.writerow(CSV_HEADER)
        map(writor.writerow, lines)
        return datafile

    def _createRequest(self, data, filename):
        """Create the request to be returned.

        Add the right header and the CSV file.
        """
        self.request.response.addHeader('Content-Disposition', "attachment; filename=%s" % filename)
        self.request.response.addHeader('Content-Type', "text/csv")
        self.request.response.addHeader('Content-Length', "%d" % len(data))
        self.request.response.addHeader('Pragma', "no-cache")
        self.request.response.addHeader('Cache-Control', "must-revalidate, post-check=0, pre-check=0, public")
        self.request.response.addHeader('Expires', "0")
        return data

    def getVersusEventos(self):
        """Return all VersusEvento."""
        eventos = []
        papeis_eventos = []
        result = self.catalog(portal_type='VersusEvento')
        for item in result:
            VersusConcluintes = self.catalog(portal_type='VersusConcluintes', path={'query':item.getPath()})
            id_edicao = 0
            if VersusConcluintes:
                obj = VersusConcluintes[0].getObject()
                id_edicao = obj.getEdicao()
                for papel in obj.getPapeis():
                    papel_evento = papel.copy()
                    papel_evento['filter'] = id_edicao
                    papel_evento['id'] = "%s - %s" % (papel['id'], id_edicao)
                    papeis_eventos.append(papel_evento)
            eventos.append({'value':item.UID, 'title':item.Title, 'filter': id_edicao})
        return {'eventos': eventos, 'papeis': papeis_eventos}

    def _insert_versus_participant(self, participants):
        """
        """
        evento = self.request.form.get('versus_evento', None)
        option = self.request.form.get('versus_option', None)
        if evento:
            nomes_certificados = []
            for participant in participants:
                versus_cadastro = self._factoryVersusCadastro(participant)
                if versus_cadastro:
                    formulario_vivencia = self._factoryVersusFormulario(participant)
                    if formulario_vivencia:
                        if option == 'selecionado':
                            self._doTransition(formulario_vivencia, "aprovado")
                            cop = self.request.form.get('community_insert', None)
                            formulario_vivencia.setComunidade(cop)
                        elif option == 'concluido':
                            self._doTransition(formulario_vivencia, "participou")
                            nomes_certificados.append(participant.get('fullname').strip())
                        formulario_vivencia.setVersuscadastros(versus_cadastro)
                        formulario_vivencia.reindexObject()
                        formulario_vivencia.reindexObjectSecurity()
            if option == 'concluido' and nomes_certificados:
                self._export_certificado(nomes_certificados)

        return False

    def _factoryVersusCadastro(self, participant):
        """Create a VersusCadastro of participant."""
        username = participant.get('username')
        user_versus_cadastro = self.catalog(portal_type='VersusCadastro',
                                            Creator=username)
        if user_versus_cadastro:
            versus_cadastro = user_versus_cadastro[0].getObject()
        else:
            result = self.catalog(portal_type='VersusFolderCadastros')
            if result:
                fullname = participant.get('fullname').strip()
                obj = result[0].getObject()
                url = self._setUrl(obj, fullname)
                obj.invokeFactory('VersusCadastro', url,
                                  title=fullname,
                                  creators=[username,],)
                versus_cadastro = getattr(obj, url)
            pm = getToolByName(self.context, 'portal_membership')
            owner = pm.getMemberById(username).getUser()
            versus_cadastro.changeOwnership(owner, recursive=False)
            versus_cadastro.manage_addLocalRoles(username, ["Owner",])
        self._setFormAttr(versus_cadastro, VERSUS_CADASTRO, participant)
        versus_cadastro.setTermo_compromisso(True)
        versus_cadastro.reindexObject()
        versus_cadastro.reindexObjectSecurity()
        return versus_cadastro

    def _factoryVersusFormulario(self, participant):
        """Create a VersusEstudanteFormulario, VersusFacilitadorFormulario
        or VersusComissaoFormulario of participant."""
        versus_evento = self.request.form.get('versus_evento', None)
        username = participant.get('username')
        line = [value for (key, value) in participant.iteritems()]
        if versus_evento:
            versus_evento = self.catalog(UID=versus_evento)[0]
            path = versus_evento.getPath()
            modalidade = participant.get('modalidade')
            estadovivencia = participant.get('estadovivencia', "").strip()
            portal_type = None
            if modalidade:
                portal_type_options = {
                    "vivente": "VersusEstudantesFormulario",
                    "facilitador": "VersusFacilitadoresFormulario",
                    "comissao": "VersusComissaoFormulario",
                }
                portal_type = portal_type_options.get(modalidade.lower(), None)

            if not modalidade or not portal_type or not estadovivencia:
                self.invalidLines.append(line)
                return False
            user_inscricao = self.catalog(path={'query':path},
                                          portal_type=portal_type,
                                          Creator=username,
                                          estadovivencia=estadovivencia,)
            if user_inscricao:
                return user_inscricao[0].getObject()
            else:
                obj = versus_evento.getObject()
                fullname = participant.get('fullname').strip()
                url = self._setUrl(obj, fullname)
                obj.invokeFactory(portal_type, url,
                                  title=fullname,
                                  creators=[username,],
                                  estadovivencia=estadovivencia,)
                formulario_vivencia = getattr(obj, url)
                pm = getToolByName(self.context, 'portal_membership')
                owner = pm.getMemberById(username).getUser()
                formulario_vivencia.changeOwnership(owner, recursive=False)
                formulario_vivencia.manage_addLocalRoles(username, ["Owner",])
                formulario_vivencia.setRegiaovivencia(participant.get('regiao_vivencia', ''))
                if portal_type in ['VersusEstudantesFormulario', 'VersusFacilitadoresFormulario']:
                    self._setFormAttr(formulario_vivencia, VERSUS_FORM_VIVENCIA, participant)
                return formulario_vivencia
            return False

    def _export_certificado(self, names=[]):
        """ Export certificado."""
        regiao = self.request.form.get('local', None)
        periodo = self.request.form.get('periodo', '')
        carga_horaria = self.request.form.get('carga_horaria', 0)
        papel = self.request.form.get('papel', None)

        if names and regiao and papel:
            papel = papel.split("-")
            edicao = int(papel[1].strip())
            papel = int(papel[0].strip())
            if carga_horaria.isdigit():
                carga_horaria = int(carga_horaria)
            else:
                carga_horaria = 0

            datafile_certificado = StringIO()
            datafile_certificado = os.path.dirname(os.path.abspath(__file__))
            datafile_certificado = datafile_certificado.replace("browser", "export_certificados")
            datafile_certificado = "%s/certificados_%s.csv" % (datafile_certificado, datetime.now().strftime("%d_%m_%Y_%H_%M_%S"))
            out = open(datafile_certificado, "w")

            writer = csv.writer(out)
           # para cada participante gerar um registro no CSV
            for name in names:
                row = [name, edicao, regiao, papel, periodo, carga_horaria,]
                writer.writerow(row)
            out.close()

            generic_methods = GenericMethods(self.context)
            generic_methods.import_csv(datafile_certificado)
        return True

    def _setUrl(self, obj, title):
        """Return a valid url."""
        url = normalize('NFKD', title.decode("utf-8")).encode('ASCII','ignore').replace(" ", "-").lower()
        count = 1
        while getattr(obj, url, False):
            if count > 1:
                url = url[:-len(str(count))] + "%s" % count
            else:
                url += "-%s" % count
            count += 1
        return url

    def _doTransition(self, obj, transition):
        """Do transition for versus_formulario_workflow."""
        pw = getToolByName(obj, 'portal_workflow')
        status = pw.getStatusOf("versus_formulario_workflow", obj)
        state = status['review_state']
        while state != transition:
            if state == "privado":
                pw.portal_workflow.doActionFor(obj, "enviado")
            elif state == "enviado":
                if transition in ("aprovado", "participou"):
                    pw.portal_workflow.doActionFor(obj, "aprovado")
            elif state == "aprovado":
                if transition == "enviado":
                    pw.portal_workflow.doActionFor(obj, "enviado")
                elif transition == "participou":
                    pw.portal_workflow.doActionFor(obj, "participou")
            elif state == "participou":
                if transition in ("enviado", "aprovado"):
                    pw.portal_workflow.doActionFor(obj, "aprovado")
            obj.reindexObject()
            obj.reindexObjectSecurity()
            status = pw.getStatusOf("versus_formulario_workflow", obj)
            state = status['review_state']
        return True

    def _setFormAttr(self, obj, fields, participant):
        """ Set from attr."""
        for field, key in fields:
            value = participant.get(key, '')
            form_field = obj.getField(field)
            if form_field.type == 'datetime':
                try:
                    value = DateTime(value)
                except:
                    continue
            elif form_field.type == 'integer':
                if value.isdigit():
                    value = int(value)
                else:
                    continue
            try:
                setattr(obj, field, value)
            except:
                pass
        return True
