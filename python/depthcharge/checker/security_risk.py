# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>

"""
Classes for aggregating security risk information and collections of findings.
"""

import enum
import json
import re

from ..uboot import UBootVersion

_BOLD_RE = re.compile(r'\*\*(?P<ident>[a-zA-Z0-9_: -]+)\*\*')


class SecurityImpact(enum.IntFlag):
    """
    Enumerated flags (:py:class:`enum.IntFlag`) that describe the impact of a :py:class:`SecurityRisk`.

    The integer value of each flag roughly increases with impact. Of course,
    context matters and ultimately the context surrounding a device and its
    threat model ultimately define this. Think of this as simply an
    approximation that can be used to sort lists in a reasonable manner.
    """

    NONE = 0
    """
    No immediate security risk; informational note.
    """

    UNKNOWN = (1 << 0)
    """
    The security impact is unclear or otherwise not yet known.
    """

    DOS = (1 << 1)
    """
    The system is rendered temporarily inoperable and must be power cycled to recover.
    """

    PDOS = (1 << 2)
    """
    The system is rendered permanently inoperable and cannot be recovered by users.
    In more severe cases, the system may not be recoverable even with vendor support.
    """

    INFO_LEAK = (1 << 6)
    """
    Behavior discloses information that may aid in reverse engineering efforts or
    exploiting security vulnerabilities on the system.
    """

    ATTACK_SURFACE = (1 << 7)
    """
    Feature or behavior increases bootloader's attack surface beyond
    that which is necessitated by its functional requirements.
    """

    RD_MEM = (1 << 8)
    """
    Operation can be abused to read memory at an attacker-controlled address.
    """

    LIMITED_WR_MEM = (1 << 9)
    """
    Operation can be abused to perform a limited, but attacker-controlled memory write.
    The address and/or value written are constrained, or the write is otherwise unlikely
    to result in arbitrary code execution due to other mitigating factors.
    """

    WEAK_AUTH = (1 << 10)
    """
    Authentication mechanism or underlying algorithm contains known weaknesses or
    its use is otherwise inconsistent with modern security standards and best practices.
    """

    VERIFICATION_BYPASS = (1 << 16)
    """
    One or more security-critical verifications (or operations) can be bypassed.
    """

    EXEC = (1 << 23)
    """
    Operation can be abused to directly execute arbitrary code,
    provided that there exists a means to load code.
    """

    WR_MEM = (1 << 24)
    """
    Operation can be abused to read write memory at an attacker-controlled
    address, potentially leading to execution of attacker-supplied code.
    """

    # Override to achieve desired string representation
    def __str__(self):
        s = self.__repr__()
        start = s.index('.') + 1
        end = s.index(':')
        return s[start:end].replace('|', '+')

    def describe(self, html=False) -> str:
        """
        Return a string describing the aggregate security impact.
        """

        if self == self.NONE:
            ret = 'No immediate security risk; informational note.\n\n'
        else:
            ret = ''

        if self == self.UNKNOWN:
            ret += ('**Unknown impact:** '
                    'The security impact associated with the relevant defect or configuration is \n'
                    'not entirely clear or known. Additional factors or more context are likely \n'
                    'required before the impact, if any, can be realized.\n\n')

        if self & self.INFO_LEAK:
            ret += ('**Information leak:** '
                    'Behavior discloses information that may aid in reverse engineering efforts \n'
                    'or actively exploiting security vulnerabilities on the system.\n\n')

        if self & self.ATTACK_SURFACE:
            ret += ('**Increased attack surface:** '
                    "Feature or behavior increases bootloader's attack surface \n"
                    'beyond that which is necessitated by its functional requirements.\n\n')

        if self & self.DOS:
            ret += ('**Denial of Service:** '
                    "The system is temporarily rendered inoperable until it's power cycled.\n\n")

        if self & self.PDOS:
            ret += ('**Persistent Denial of Service:** '
                    'The system is rendered inoperable and the DOS state persists across power'
                    'cycles.\n\n')

        if self & self.RD_MEM:
            ret += ('**Memory read primitive:** '
                    'Operation can be abused to read memory at an attacker-controlled address.\n\n')

        if self & self.LIMITED_WR_MEM:
            ret += ('**Limited memory write primitive:** '
                    'Operation can be abused to perform a limited, but attacker-controlled memory \n'
                    'write. The address and/or value written are constrained, or the write is \n'
                    'otherwise unlikely to result in arbitrary code execution due to other \n'
                    'mitigating factors.\n\n')

        if self & self.WEAK_AUTH:
            ret += ('**Weak authentication:** '
                    'Authentication mechanism or underlying algorithm contains known \n'
                    'weaknesses or its use is otherwise inconsistent with modern security \n'
                    'standards and best practices.\n\n')

        if self & self.VERIFICATION_BYPASS:
            ret += ('**Verification bypass:** '
                    'One or more security-critical verifications (or associated operations) can be bypassed.\n\n')

        if self & self.EXEC:
            ret += ('**Execution primitive:** '
                    'Operation can be abused to directly execute arbitrary code, \n'
                    'provided that there exists a means to load code.\n\n')

        if self & self.WR_MEM:
            ret += ('**Memory write primitive:** '
                    'Operation can be abused to write memory at an attacker-controlled \n'
                    'address, potentially leading to execution of attacker-supplied code.\n\n')

        if html:
            ret = ret.replace('\n', '<br/>\n')
            ret = _BOLD_RE.sub(r'<strong>\g<ident></strong>', ret)

        return ret


class SecurityRisk:
    """
    Encapsulates information about a potential security risk.

    :Important: Identifiers must be unique, as these are used to differentiate one
        :py:class:`SecurityRisk` from another when coalescing results.
    """

    def __init__(self, identifier, impact, source, summary, description, recommendation,
                 affected_versions: tuple = None):
        """
        Instantiate a new :py:class:`SecurityRisk` object.

        Refer to this class's properties for a description of each parameter.

        If the :py:class:`SecurityRisk` applies only to specific versions,
        provide the inclusive range of affected versions as a ``(min, max)`` tuple.
        For example CVE-2019-13104 affects U-Boot 2016.11-rc1 through 2019.07-rc4. The
        corresponding tuple would be ``('2016.11-rc1', '2019.07-rc4')``.
        """

        self._ident = identifier
        self._impact = impact
        self._summary = summary
        self._source = source
        self._description = description
        self._recommendation = recommendation
        self._min_version = None
        self._max_version = None

        if not isinstance(self._impact, SecurityImpact):
            err = "Expected type SecurityImpact for 'impact', got {:s}"
            raise TypeError(err.format(type(self._impact).__name__))

        if affected_versions is not None:
            self._min_version = affected_versions[0]
            self._max_version = affected_versions[1]

    # When coalescing SecurityRisk objects, it doesn't make sense to have
    # the same risk repeated multiple times just because we discovered
    # the same finding via multiple methods.
    #
    # Per our API documentation for this class, we require and rely upon
    # the uniqueness of the identifier
    #
    # Comparisson of a SecurityRisk against str is also permitted.
    # This is allows us to test if a SecurityRisk is in a set, as
    # is done in the Report class.
    def __eq__(self, other) -> bool:
        if hasattr(other, 'identifier'):
            return self.identifier == other.identifier

        if isinstance(other, str):
            return self.identifier == other

        return False

    def __hash__(self):
        return self.identifier.__hash__()

    def __repr__(self):
        return self.__class__.__name__ + '<' + self.identifier + '>'

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)

    @property
    def identifier(self) -> str:
        """
        A short string that uniquely identifies a specific security risk.
        """
        return self._ident

    @property
    def summary(self) -> str:
        """
        A concise summary of the security risk, suitable for use as a title heading.
        """
        return self._summary

    @property
    def impact(self):
        """
        The potential impact of a security vulnerability, encoded as a :py:class:`SecurityImpact`.
        """
        return self._impact

    @property
    def impact_str(self) -> str:
        """
        The potential impact of a security vulnerability, represented as a string of one or more
        abbreviations.
        """
        return str(self._impact)

    @property
    def source(self) -> str:
        """
        A string denoting the file and/or location that was used to deduce the presence of a
        potential security risk.
        """
        return self._source

    @source.setter
    def source(self, value):
        self._source = value

    @property
    def description(self) -> str:
        """
        A string that provides a more detailed explanation of the potential security risk - what it
        is, why it matters, and how it could impact stakeholders and users.
        """
        return self._description

    @property
    def recommendation(self) -> str:
        """
        A string containing high-level and generic guidance for eliminating or mitigating
        a reported security risk.

        This is almost never appropriate as one-size-fits-all guidance; all products and threat
        models vary in their own unique ways. In many cases, the recommendation is *"just turn this
        off"*, which obviously doesn't account for how any relevant requirements (e.g. for failure
        analysis of returned units) can be satisfied in a more secure manner.

        Instead, consider is this a starting point for further discussion about remediation efforts.
        """
        return self._recommendation

    def to_dict(self) -> dict:
        """
        Return the :py:class:`SecurityRisk` object as a dictionary with the following keys,
        each associated with a value of the listed property.

        * ``'identifier'``      - :py:meth:`identifier`
        * ``'summary'``         - :py:meth:`summary`
        * ``'impact'``          - :py:meth:`impact`
        * ``'source'``          - :py:meth:`source`
        * ``'description'``     - :py:meth:`description`
        * ``'recommendation'``  - :py:meth:`recommendation`

        """
        return {
            'identifier':       self.identifier,
            'impact':           self.impact,
            'source':           self.source,
            'description':      self.description,
            'recommendation':   self.recommendation,
        }

    @classmethod
    def from_dict(cls, d: dict):  # pylint: disable=invalid-name # jynik[OK].
        """
        Create a :py:class:`SecurityRisk` from a dictionary.

        Refer to :py:meth:`to_dict()` for the supported key-value pairs.
        """
        return cls(
            d['identifier'],
            d['impact'],
            d['source'],
            d['summary'],
            d['description'],
            d['recommendation'],
            affected_versions=d.get('affected_versions', None)
        )

    def applicable_to_version(self, version: str) -> bool:
        """
        Returns ``True`` if this security risk may be applicable to the specified U-Boot
        version, and ``False`` otherwise.
        """

        # Version is not relevant
        if not self._min_version or not self._max_version:
            return True

        if isinstance(version, str):
            version = UBootVersion(version)
        elif isinstance(version, UBootVersion):
            pass
        else:
            err = 'Unexpected type for `version` parameter: '
            raise TypeError(err + type(version).__name__)

        return version.in_range(self._min_version, self._max_version)
