class PimManager < Formula
  desc "TUI for activating Microsoft PIM assignments"
  homepage "https://github.com/mathwro/pim-manager"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.5.0/pim-manager_0.5.0_darwin_arm64.tar.gz"
      sha256 "dce948a5395d70b4a3dd59dee40d043f75609465d394e8c295555f175c487350"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.5.0/pim-manager_0.5.0_darwin_amd64.tar.gz"
      sha256 "895f2b1cbfb2e5eb5ae54913e53e2c887d7a0de273cd1940f0ff303a1b74cfb2"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.5.0/pim-manager_0.5.0_linux_arm64.tar.gz"
      sha256 "1a393e66cb41fd84fc91d5df9b25823418923699ef3e6ca2411dcdb02f6a877d"
    end
    on_intel do
      url "https://github.com/mathwro/pim-manager/releases/download/v0.5.0/pim-manager_0.5.0_linux_amd64.tar.gz"
      sha256 "cf1bbbba1a59184358f5874cfcbdd78c056742624b5c5a1687e1b472eee57410"
    end
  end

  def install
    bin.install "pim-manager"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pim-manager --version")
  end
end
