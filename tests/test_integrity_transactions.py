"""Simulación optimista de conflictos/commit; sin conexiones ni Firebase remoto."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from teacher_store import Snapshot
from authorization import AccessDenied
from integrity_service import IntegrityError, mutate_user
from promotion_service import promote_student, promotion_data


class Conflict(Exception):
    pass


class Ref:
    def __init__(self, db, name, key):
        self.db, self.name, self.id = db, name, key

    def get(self, transaction=None):
        with self.db.lock:
            if transaction:
                transaction.reads[(self.name, self.id)] = self.db.versions.get((self.name, self.id), 0)
            return Snapshot(self.id, deepcopy(self.db.data.get(self.name, {}).get(self.id)))


class Query:
    def __init__(self, db, name, filters=()):
        self.db, self.name, self.filters = db, name, filters

    def document(self, key):
        return Ref(self.db, self.name, key)

    def where(self, field, op, value):
        assert op == '=='
        return Query(self.db, self.name, self.filters + ((field, value),))

    def stream(self, transaction=None):
        with self.db.lock:
            keys = list(self.db.data.get(self.name, {}))
        for key in keys:
            doc = self.document(key).get(transaction)
            if all(doc.to_dict().get(f) == v for f, v in self.filters):
                yield doc


class Transaction:
    def __init__(self, db):
        self.db, self.reads, self.pending = db, {}, []

    def set(self, ref, values):
        self.pending.append(('set', ref, deepcopy(values)))

    def update(self, ref, values):
        self.pending.append(('update', ref, deepcopy(values)))

    def delete(self, ref):
        self.pending.append(('delete', ref, None))

    def commit(self):
        with self.db.lock:
            if any(self.db.versions.get(key, 0) != version for key, version in self.reads.items()):
                raise Conflict()
            if self.db.fail:
                raise RuntimeError('Fallo simulado de commit')
            for action, ref, values in self.pending:
                if action == 'delete':
                    self.db.data[ref.name].pop(ref.id, None)
                elif action == 'update':
                    self.db.data[ref.name][ref.id].update(values)
                else:
                    self.db.data.setdefault(ref.name, {})[ref.id] = values
                key = ref.name, ref.id
                self.db.versions[key] = self.db.versions.get(key, 0) + 1
                self.db.writes.append((action, ref.name, ref.id))


def simulated_transactional(callback):
    def run(initial):
        db = initial.db
        for attempt in range(6):
            tx = initial if attempt == 0 else Transaction(db)
            outcome = callback(tx)
            if attempt == 0 and db.barrier:
                db.barrier.wait(timeout=5)
            hook, db.hook = db.hook, None
            if hook:
                hook()
            try:
                tx.commit()
            except Conflict:
                db.retries += 1
                continue
            if db.lost_ack:
                db.lost_ack = False
                raise RuntimeError('Confirmación perdida después de commit')
            return outcome
        raise RuntimeError('Conflictos agotados')
    return run


class MemoryDB:
    project = 'edumanager-demo'

    def __init__(self):
        self.data = {'usuarios': {
            'a': dict(rol='admin', activo=True, nombre='A'),
            'b': dict(rol='admin', activo=True, nombre='B'),
            'teacher': dict(rol='docente', activo=True, nombre='Docente')},
            'alumnos': {'s': dict(nie='1', grado_actual='Primer Grado', estado='Activo',
                                  ciclo_lectivo=2027, turno='Matutino',
                                  historial_academico=[{'ciclo': 2025, 'nota': 'Conservar'}])}}
        self.lock = threading.RLock()
        self.versions, self.writes = {}, []
        self.fail, self.lost_ack = False, False
        self.hook, self.barrier = None, None
        self.retries = 0

    def collection(self, name):
        return Query(self, name)

    def transaction(self):
        return Transaction(self)

    def external_update(self, name, key, values):
        with self.lock:
            self.data[name][key].update(deepcopy(values))
            self.versions[(name, key)] = self.versions.get((name, key), 0) + 1


def session(actor='a', role='admin'):
    return dict(logged_in=True, user_id=actor, user_role=role)


def user_values(user='a', role='docente'):
    return dict(usuario=user, nombre='Usuario ficticio', rol=role, password_hash='hash-ficticio')


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.db = MemoryDB()
        for name, kwargs in [
            ('integrity_service.firestore.transactional', dict(side_effect=simulated_transactional)),
            ('socket.socket.connect', dict(side_effect=AssertionError('Red prohibida'))),
        ]:
            p = patch(name, **kwargs); p.start(); self.addCleanup(p.stop)

    def mutate(self, target='a', action='save', values=None, actor='a'):
        return mutate_user(self.db, target, action, values, session(actor))

    def promote(self, student='s', result='Promover', grade='Primer Grado'):
        return promote_student(self.db, student, result, grade, 2027, 2028, '01/01/2028', session())

    def last_admin(self):
        self.db.data['usuarios']['b']['rol'] = 'docente'

    def test_last_admin_demotion_denied(self):
        self.last_admin()
        with self.assertRaises(IntegrityError): self.mutate(values=user_values())
        self.assertEqual(self.db.writes, [])

    def test_last_admin_deactivation_denied(self):
        self.last_admin()
        with self.assertRaises(IntegrityError):
            self.mutate(action='deactivate', values=dict(fecha_baja='fecha', baja_realizada_por='A'))
        self.assertEqual(self.db.writes, [])

    def test_last_admin_deletion_denied(self):
        self.last_admin()
        with self.assertRaises(IntegrityError): self.mutate(action='delete')
        self.assertEqual(self.db.writes, [])

    def test_concurrent_demotions_leave_one_admin(self):
        self.db.barrier = threading.Barrier(2)
        def change(actor):
            try: return self.mutate(target=actor, values=user_values(actor), actor=actor)
            except (IntegrityError, AccessDenied): return False
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(change, ['a', 'b']))
        self.assertEqual(sum(results), 1)
        self.assertGreaterEqual(self.db.retries, 1)
        self.assertEqual(sum(r.get('rol') == 'admin' and r.get('activo') is True
                             for r in self.db.data['usuarios'].values()), 1)

    def test_create_single_user_write(self):
        self.mutate('new', values=user_values('new'))
        self.assertEqual([w for w in self.db.writes if w[1] == 'usuarios'], [('set', 'usuarios', 'new')])
        self.assertIs(self.db.data['usuarios']['new']['activo'], True)

    def test_update_preserves_link_hash_and_active(self):
        self.db.data['usuarios']['teacher'].update(id_docente='t1', activo=False)
        self.mutate('teacher', values=user_values('teacher', 'admin'))
        row = self.db.data['usuarios']['teacher']
        self.assertEqual(row['id_docente'], 't1')
        self.assertFalse(row['activo'])
        self.assertEqual(row['password_hash'], 'hash-ficticio')

    def test_repeated_identical_save_no_second_mutation(self):
        self.mutate('new', values=user_values('new'))
        writes = list(self.db.writes)
        self.assertFalse(self.mutate('new', values=user_values('new')))
        self.assertEqual(self.db.writes, writes)

    def test_user_commit_failure_changes_nothing(self):
        before = deepcopy(self.db.data); self.db.fail = True
        with self.assertRaises(RuntimeError): self.mutate('new', values=user_values('new'))
        self.assertEqual(self.db.data, before)
        self.assertEqual(self.db.writes, [])

    def test_deactivate_and_reactivate(self):
        self.mutate('b', 'deactivate', dict(fecha_baja='fecha', baja_realizada_por='A'))
        self.assertFalse(self.db.data['usuarios']['b']['activo'])
        self.mutate('b', 'reactivate')
        self.assertTrue(self.db.data['usuarios']['b']['activo'])

    def test_delete_other_admin_when_one_remains(self):
        self.mutate('b', 'delete')
        self.assertNotIn('b', self.db.data['usuarios'])

    def test_protected_developer_and_self_delete(self):
        for target in ['david', 'a']:
            with self.assertRaises(IntegrityError): self.mutate(target, 'delete')

    def test_teacher_cannot_mutate_users(self):
        with self.assertRaises(AccessDenied):
            mutate_user(self.db, 'new', 'save', user_values('new'), session('teacher', 'docente'))
        self.assertFalse(self.db.writes)

    def test_teacher_cannot_promote(self):
        with self.assertRaises(AccessDenied):
            promote_student(self.db, 's', 'Promover', 'Primer Grado', 2027, 2028, 'fecha', session('teacher', 'docente'))

    def test_actor_revoked_before_commit_is_rechecked(self):
        self.db.hook = lambda: self.db.external_update('usuarios', 'a', {'activo': False})
        with self.assertRaises(AccessDenied): self.promote()
        self.assertEqual(self.db.writes, [])

    def test_success_preserves_previous_history(self):
        self.assertEqual(self.promote().status, 'promovido')
        row = self.db.data['alumnos']['s']
        self.assertEqual(row['grado_actual'], 'Segundo Grado')
        self.assertEqual(row['ciclo_lectivo'], 2028)
        self.assertEqual(row['historial_academico'][0], {'ciclo': 2025, 'nota': 'Conservar'})
        self.assertEqual(len(row['historial_academico']), 2)

    def test_promotion_failure_no_student_changes(self):
        before = deepcopy(self.db.data); self.db.fail = True
        with self.assertRaises(RuntimeError): self.promote()
        self.assertEqual(self.db.data, before)

    def test_duplicate_promotion_rejected(self):
        self.promote(); self.assertEqual(self.promote().status, 'rechazado')
        self.assertEqual(len(self.db.writes), 1)

    def test_history_concurrent_append_survives_retry(self):
        added = [{'ciclo': 2025, 'nota': 'Conservar'}, {'ciclo': 2026, 'nota': 'Concurrente'}]
        self.db.hook = lambda: self.db.external_update('alumnos', 's', {'historial_academico': added})
        self.assertEqual(self.promote().status, 'promovido')
        self.assertEqual(self.db.retries, 1)
        self.assertEqual(self.db.data['alumnos']['s']['historial_academico'][:2], added)
        self.assertEqual(len(self.db.data['alumnos']['s']['historial_academico']), 3)

    def test_concurrent_duplicate_only_one_commit(self):
        self.db.barrier = threading.Barrier(2)
        with ThreadPoolExecutor(2) as pool:
            outcomes = list(pool.map(lambda _: self.promote().status, range(2)))
        self.assertCountEqual(outcomes, ['promovido', 'rechazado'])
        self.assertEqual(len(self.db.writes), 1)

    def test_new_cycle_or_grade_rejected(self):
        for field, value in [('ciclo_lectivo', 2026), ('grado_actual', 'Segundo Grado'), ('estado', 'Baja')]:
            before = deepcopy(self.db.data['alumnos']['s'])
            self.db.data['alumnos']['s'][field] = value
            self.assertEqual(self.promote().status, 'rechazado')
            self.db.data['alumnos']['s'] = before
        self.assertFalse(self.db.writes)

    def test_malformed_history_blocked(self):
        self.db.data['alumnos']['s']['historial_academico'] = None
        with self.assertRaises(IntegrityError): self.promote()
        self.assertFalse(self.db.writes)

    def test_no_process_omitted(self):
        self.assertEqual(self.promote(result='No procesar').status, 'omitido')
        self.assertFalse(self.db.writes)

    def test_lost_ack_retry_does_not_duplicate(self):
        self.db.lost_ack = True
        with self.assertRaises(RuntimeError): self.promote()
        self.assertEqual(self.promote().status, 'rechazado')
        self.assertEqual(len(self.db.writes), 1)

    def test_invalid_result_or_cycles_denied(self):
        with self.assertRaises(IntegrityError): self.promote(result='Inventado')
        with self.assertRaises(IntegrityError):
            promote_student(self.db, 's', 'Promover', 'Primer Grado', 2027, 2030, 'fecha', session())

    def test_repeater_and_graduate_preserve_rules(self):
        self.assertEqual(self.promote(result='No promovido').status, 'no_promovido')
        self.assertEqual(self.db.data['alumnos']['s']['grado_actual'], 'Primer Grado')
        self.db.data['alumnos']['s'].update(grado_actual='Noveno Grado', ciclo_lectivo=2027, historial_academico=[])
        self.assertEqual(self.promote(grade='Noveno Grado').status, 'graduado')
        self.assertFalse(self.db.data['alumnos']['s']['activo'])
        self.assertEqual(self.db.data['alumnos']['s']['ciclo_lectivo'], 2027)

    def test_fourth_grade_changes_shift_unchanged(self):
        self.db.data['alumnos']['s']['grado_actual'] = 'Cuarto Grado'
        self.promote(grade='Cuarto Grado')
        self.assertEqual(self.db.data['alumnos']['s']['turno'], 'Vespertino')

    def test_missing_transaction_support_fails_closed(self):
        self.db.transaction = None
        with self.assertRaises(TypeError): self.promote()
        self.assertFalse(self.db.writes)

    def test_production_project_denied(self):
        self.db.project = 'production'
        with self.assertRaises(AccessDenied): self.promote()
        self.assertFalse(self.db.writes)

    def test_concurrent_deletions_keep_an_administrator(self):
        self.db.barrier = threading.Barrier(2)
        def change(actor):
            try:
                return self.mutate('b' if actor == 'a' else 'a', 'delete', actor=actor)
            except (IntegrityError, AccessDenied):
                return False
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(change, ['a', 'b'])), 1)
        self.assertEqual(len([row for row in self.db.data['usuarios'].values()
                             if row['rol'] == 'admin' and row['activo'] is True]), 1)

    def test_concurrent_deactivations_keep_an_administrator(self):
        self.db.barrier = threading.Barrier(2)
        def change(actor):
            try:
                return self.mutate('b' if actor == 'a' else 'a', 'deactivate',
                                   dict(fecha_baja='fecha', baja_realizada_por=actor), actor=actor)
            except (IntegrityError, AccessDenied):
                return False
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(change, ['a', 'b'])), 1)
        self.assertEqual(sum(row['rol'] == 'admin' and row['activo'] is True
                             for row in self.db.data['usuarios'].values()), 1)

    def test_invalid_guard_blocks_user_mutation(self):
        self.db.data['_integrity'] = {'administradores': {'revision': 'invalid'}}
        with self.assertRaises(IntegrityError): self.mutate('new', values=user_values('new'))
        self.assertFalse(self.db.writes)

    def test_unknown_role_and_user_path_blocked(self):
        with self.assertRaises(IntegrityError): self.mutate(values=user_values('a', 'unknown'))
        with self.assertRaises(IntegrityError): self.mutate('bad/path', values=user_values('bad/path'))
        self.assertFalse(self.db.writes)

    def test_legacy_cycle_remains_origin_and_string_history_prevents_duplicate(self):
        self.db.data['alumnos']['s'].pop('ciclo_lectivo')
        self.assertEqual(self.promote().status, 'promovido')
        self.db.data['alumnos']['s']['historial_academico'][-1]['ciclo'] = '2027'
        self.assertEqual(self.promote().status, 'rechazado')

    def test_changed_grade_during_commit_is_rejected_on_retry(self):
        self.db.hook = lambda: self.db.external_update('alumnos', 's', {'grado_actual': 'Tercer Grado'})
        self.assertEqual(self.promote().status, 'rechazado')
        self.assertFalse(self.db.writes)



class IntegrityViewTests(unittest.TestCase):
    def setUp(self):
        IntegrityTests.setUp(self)

    def app(self, module):
        from streamlit.testing.v1 import AppTest
        script = '''
import streamlit as st
from datetime import date
from auth import generar_hash
from views.configuracion import mostrar_configuracion
from views.promocion import mostrar_promocion
if st.session_state['module'] == 'users':
    mostrar_configuracion(st.session_state['db'], generar_hash, lambda _: None)
else:
    mostrar_promocion(st.session_state['db'], lambda: date(2028,1,1), 2027, 2028)
'''
        app = AppTest.from_string(script)
        for key, value in dict(session(), db=self.db, module=module).items():
            app.session_state[key] = value
        return app.run(timeout=15)

    def fill_user(self, app, user='new', role='docente'):
        for label, value in [('Usuario (ID)', user), ('Contraseña', 'ficticia-123'), ('Nombre Real', 'Ficticio')]:
            next(e for e in app.text_input if e.label == label).set_value(value)
        next(e for e in app.selectbox if e.label == 'Rol').set_value(role)
        return next(e for e in app.button if e.label == '💾 Guardar Usuario').click().run()

    def test_user_form_single_commit_and_rerun_not_resubmit(self):
        app = self.fill_user(self.app('users'))
        self.assertFalse(app.exception)
        self.assertEqual(len([w for w in self.db.writes if w[1] == 'usuarios']), 1)
        from auth import verificar_password
        self.assertTrue(verificar_password('ficticia-123', self.db.data['usuarios']['new']['password_hash']))
        app.run()
        self.assertEqual(len([w for w in self.db.writes if w[1] == 'usuarios']), 1)

    def test_user_form_failure_has_no_success(self):
        self.db.fail = True
        app = self.fill_user(self.app('users'))
        self.assertFalse(app.exception)
        self.assertTrue(any('No se pudo guardar' in e.value for e in app.error))
        self.assertFalse(any('creado' in e.value for e in app.success))
        self.assertNotIn('new', self.db.data['usuarios'])

    def test_form_rejects_last_admin_demotion(self):
        self.db.data['usuarios']['b']['rol'] = 'docente'
        app = self.fill_user(self.app('users'), user='a')
        self.assertTrue(any('administrador activo' in e.value for e in app.error))
        self.assertEqual(self.db.data['usuarios']['a']['rol'], 'admin')

    def test_promotion_confirmations_and_partial_counts(self):
        self.db.data['alumnos']['s2'] = deepcopy(self.db.data['alumnos']['s'])
        self.db.data['alumnos']['s2']['nie'] = '2'
        original = Transaction.commit
        def fail_second(tx):
            if any(ref.id == 's2' for _, ref, _ in tx.pending):
                raise RuntimeError('Fallo del segundo alumno')
            return original(tx)
        p = patch.object(Transaction, 'commit', fail_second)
        p.start(); self.addCleanup(p.stop)
        app = self.app('promotion')
        next(e for e in app.selectbox if e.label == 'Grado a procesar').set_value('Primer Grado').run()
        next(e for e in app.button if 'EJECUTAR' in e.label).click().run()
        self.assertFalse(self.db.writes)
        self.assertTrue(app.error)
        next(e for e in app.text_input if 'PROMOVER' in e.label).set_value('PROMOVER')
        next(e for e in app.checkbox if 'revisé' in e.label).check()
        next(e for e in app.button if 'EJECUTAR' in e.label).click().run()
        self.assertFalse(app.exception)
        values = {e.label: e.value for e in app.metric}
        self.assertEqual(values['✅ Promovidos'], '1')
        self.assertTrue(any('Errores de escritura o confirmación: 1' in e.value for e in app.markdown))
        self.assertTrue(app.warning)
        self.assertFalse(any('Proceso de cierre finalizado' in e.value for e in app.success))
        self.assertEqual(self.db.data['alumnos']['s']['ciclo_lectivo'], 2028)
        self.assertEqual(self.db.data['alumnos']['s2']['ciclo_lectivo'], 2027)

    def test_promotion_denied_write_counted_as_rejected(self):
        app = self.app('promotion')
        next(e for e in app.selectbox if e.label == 'Grado a procesar').set_value('Primer Grado').run()
        next(e for e in app.text_input if 'PROMOVER' in e.label).set_value('PROMOVER')
        next(e for e in app.checkbox if 'revisé' in e.label).check()
        with patch('views.promocion.promote_student', side_effect=AccessDenied('Permiso revocado')):
            next(e for e in app.button if 'EJECUTAR' in e.label).click().run()
        self.assertEqual(next(e.value for e in app.metric if e.label == '✅ Promovidos'), '0')
        self.assertTrue(any('Rechazados: 1' in e.value and 'confirmación: 0' in e.value for e in app.markdown))
        self.assertFalse(self.db.writes)

    def test_promotion_summary_counts_omitted_and_confirmed(self):
        self.db.data['alumnos']['s2'] = deepcopy(self.db.data['alumnos']['s'])
        self.db.data['alumnos']['s2']['nie'] = '2'
        app = self.app('promotion')
        next(e for e in app.selectbox if e.label == 'Grado a procesar').set_value('Primer Grado').run()
        next(e for e in app.text_input if 'PROMOVER' in e.label).set_value('PROMOVER')
        next(e for e in app.checkbox if 'revisé' in e.label).check()
        def editor(df, **kwargs):
            modified = df.copy()
            modified.loc[1, 'Resultado'] = 'No procesar'
            return modified
        with patch('views.promocion.st.data_editor', side_effect=editor):
            next(e for e in app.button if 'EJECUTAR' in e.label).click().run()
        self.assertEqual(next(e.value for e in app.metric if e.label == '✅ Promovidos'), '1')
        self.assertTrue(any('Omitidos: 1' in e.value and 'Rechazados: 0' in e.value for e in app.markdown))
        self.assertEqual(len(self.db.writes), 1)
