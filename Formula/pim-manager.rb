class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.2/pim-manager_0.4.2_darwin_arm64.tar.gz"
      sha256 "2f76aed3ef99b075d4c88c44d0a60c9af9532b2671d740abd2a87d2878f93b43"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.2/pim-manager_0.4.2_darwin_amd64.tar.gz"
      sha256 "40b4221fd07ddaaa41aa8caacf99c2e179064f5c0cce21b53e37717c3ec57680"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.2/pim-manager_0.4.2_linux_arm64.tar.gz"
      sha256 "51751d76d5642b6c4e780ab9f0c424cae167d87dc2b04057aec8d1d766a7b359"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.4.2/pim-manager_0.4.2_linux_amd64.tar.gz"
      sha256 "3b78f5b3d1e65f9271776f3a469622118a456a7a725d935d0c2b89388ab05d85"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
